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

    if action == "draft_slack":
        context = kwargs.get("context", "")
        purpose = kwargs.get("purpose", "update")

        # Dynamic token limit based on content size
        context_length = len(context.split())
        max_tokens = min(2000, max(800, context_length * 5))

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"""Draft a complete, professional Slack message. Do NOT truncate or cut off.

Purpose: {purpose}
Context: {context}

Requirements:
- Start with a relevant emoji and bold title
- Be specific — include actual task names, numbers, dates from the context
- Use bullet points for lists
- If there are tasks, list ALL of them
- End with a clear next step or call to action
- Write the COMPLETE message — never stop mid-sentence
- Ensure the message ends with a proper closing and does not cut off.
""",
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=max_tokens
            )
        )
        draft = response.text.strip()
        return {
            "action": "draft_slack",
            "draft": draft,
            "channel": SLACK_CHANNEL,
            "message": "Slack message drafted — ready to send"
        }
    
    elif action == "send_slack":
        message = kwargs.get("message", "")
        channel = kwargs.get("channel", SLACK_CHANNEL)

        if not message:
            return {
                "action": "send_slack",
                "error": "No message provided",
                "message": "No message to send"
            }

        try:
            # Split into chunks of 3000 chars
            chunks = []
            while len(message) > 3000:
                # Find last newline before 3000
                split_at = message[:3000].rfind('\n')
                if split_at == -1:
                    split_at = 3000
                chunks.append(message[:split_at])
                message = message[split_at:].strip()
            if message:
                chunks.append(message)

            ts = None
            for i, chunk in enumerate(chunks):
                if i == 0:
                    result = slack_client.chat_postMessage(
                        channel=channel,
                        text=chunk,
                        username="ARIA — AI Chief of Staff",
                        icon_emoji=":robot_face:"
                    )
                    ts = result["ts"]
                else:
                    slack_client.chat_postMessage(
                        channel=channel,
                        text=chunk,
                        username="ARIA — AI Chief of Staff",
                        icon_emoji=":robot_face:",
                        thread_ts=ts
                    )

            log.info("Slack message sent", chunks=len(chunks))
            return {
                "action": "send_slack",
                "channel": channel,
                "timestamp": ts,
                "sent": True,
                "chunks_sent": len(chunks),
                "message": f"✅ Message sent to Slack ({len(chunks)} part(s))"
            }
        except SlackApiError as e:
            log.error("Slack error", error=str(e))
            return {
                "action": "send_slack",
                "error": str(e.response["error"]),
                "message": f"Failed: {e.response['error']}"
            }

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