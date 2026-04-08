import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google import genai
from google.genai import types
from config import settings
from db import queries

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)
slack_client = WebClient(token=settings.slack_bot_token)

SLACK_CHANNEL = "C0AQZAN1A79"


async def run_communication_agent(
    action: str,
    user_id: str = "user-aadarsh-001",
    **kwargs
) -> dict:
    log.info("CommunicationAgent started", action=action)

    # --- 1. IMPROVED DRAFTING LOGIC (Unified for both actions) ---
    if action in ["draft_slack", "draft_update"]:
        context = kwargs.get("context", "")
        purpose = kwargs.get("purpose", "update")

        # If it's a plan update, we need to fetch the actual task names
        if action == "draft_update" and kwargs.get("plan_id"):
            plan = await queries.get_plan(kwargs.get("plan_id"))
            tasks = await queries.get_tasks_by_plan(kwargs.get("plan_id"))
            # Format tasks into a string so the AI actually knows what they are
            task_list = "\n".join([f"- {t['title']} ({t['status']})" for t in tasks])
            context = f"Plan: {plan['goal_text']}\nRecent Tasks:\n{task_list}"

        # Dynamic token limit: ensure at least 1500 for those 35+ task lists
        context_length = len(context.split())
        max_tokens = max(1500, context_length * 6) 

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"""Draft a complete, professional Slack message. 
            
            CRITICAL: Do NOT truncate. You must list ALL tasks provided.
            
            Purpose: {purpose}
            Context: {context}

            Requirements:
            - Start with a 🚀 bold title
            - List EVERY task from the context (don't say "and more")
            - Use clear bullet points
            - End with a proper closing and next steps
            - If you run out of room, prioritize a clean sign-off over more data.
            """,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=max_tokens
            )
        )
        draft = response.text.strip()
        return {
            "action": action,
            "draft": draft,
            "channel": SLACK_CHANNEL,
            "message": f"Slack message drafted via {action}"
        }
    
    # --- 2. IMPROVED SEND LOGIC (Safety Chunks) ---
    elif action == "send_slack":
        message = kwargs.get("message", "")
        channel = kwargs.get("channel", SLACK_CHANNEL)

        if not message or len(message) < 5:
            return {"action": "send_slack", "error": "Message too short or empty"}

        try:
            # Slack blocks/text have limits. We split at 3500 chars.
            chunks = []
            while len(message) > 3500:
                split_at = message[:3500].rfind('\n')
                if split_at == -1: split_at = 3500
                chunks.append(message[:split_at])
                message = message[split_at:].strip()
            if message: chunks.append(message)

            ts = None
            for i, chunk in enumerate(chunks):
                # We use the icon and name defined in your ARIA requirements
                result = slack_client.chat_postMessage(
                    channel=channel,
                    text=chunk,
                    thread_ts=ts if i > 0 else None, # Threading prevents spam
                    username="ARIA — AI Chief of Staff",
                    icon_emoji=":robot_face:"
                )
                if i == 0: ts = result["ts"]

            return {"action": "send_slack", "sent": True, "chunks": len(chunks)}
            
        except SlackApiError as e:
            log.error("Slack error", error=str(e))
            return {"action": "send_slack", "error": str(e)}


    elif action == "draft_and_send":
        context = kwargs.get("context", "")
        purpose = kwargs.get("purpose", "update")

        # Draft the message
        draft_result = await run_communication_agent(
            "draft_slack",
            user_id=user_id,
            context=context,
            purpose=purpose
        )
        draft = draft_result.get("draft", "")

        # Send it
        send_result = await run_communication_agent(
            "send_slack",
            user_id=user_id,
            message=draft,
            channel=SLACK_CHANNEL
        )

        return {
            "action": "draft_and_send",
            "draft": draft,
            "sent": "error" not in send_result,
            "channel": SLACK_CHANNEL,
            "message": f"Message drafted and sent to Slack"
        }

    elif action == "draft_update":
        plan_id = kwargs.get("plan_id")
        if plan_id:
            plan = await queries.get_plan(plan_id)
            tasks = await queries.get_tasks_by_plan(plan_id)
            completed = sum(1 for t in tasks if t["status"] == "completed")
            context = f"Plan: {plan['goal_text']}. Progress: {completed}/{len(tasks)} tasks completed."
        else:
            context = kwargs.get("context", "Project update")

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"Write a brief team update Slack message for: {context}",
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=1000
            )
        )
        return {
            "action": "draft_update",
            "draft": response.text.strip(),
            "message": "Team update drafted"
        }

    else:
        return {
            "action": action,
            "error": f"Unknown action: {action}"
        }