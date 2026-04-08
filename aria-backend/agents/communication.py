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

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"""Draft a professional Slack message.

Purpose: {purpose}
Context: {context}

Requirements:
- Start with a relevant emoji
- Be concise and actionable (under 150 words)
- Use bullet points for key items
- End with a clear next step
- Sound like a real team update, not AI-generated
""",
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=300
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
            result = slack_client.chat_postMessage(
                channel=channel,
                text=message,
                username="ARIA — AI Chief of Staff",
                icon_emoji=":robot_face:"
            )
            log.info("Slack message sent",
                     channel=channel, ts=result["ts"])
            return {
                "action": "send_slack",
                "channel": channel,
                "timestamp": result["ts"],
                "message": f"✅ Message sent to Slack channel"
            }
        except SlackApiError as e:
            log.error("Slack error", error=str(e))
            return {
                "action": "send_slack",
                "error": str(e.response["error"]),
                "message": f"Failed to send: {e.response['error']}"
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
                max_output_tokens=200
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