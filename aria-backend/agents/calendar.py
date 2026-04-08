import pickle
import os
import structlog
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import settings
from db import queries

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)

# Look in multiple locations for token.pickle
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(_base, "token.pickle")
if not os.path.exists(TOKEN_PATH):
    TOKEN_PATH = os.path.join(_base, "..", "token.pickle")
if not os.path.exists(TOKEN_PATH):
    TOKEN_PATH = os.path.join(os.path.expanduser("~"), "token.pickle")

def get_calendar_service():
    """Get authenticated Google Calendar service."""
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"token.pickle not found at {TOKEN_PATH}. Run OAuth first.")
    with open(TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    return build("calendar", "v3", credentials=creds)


async def run_calendar_agent(
    action: str,
    user_id: str = "user-aadarsh-001",
    **kwargs
) -> dict:
    log.info("CalendarAgent started", action=action)

    if action == "get_upcoming":
        try:
            service = get_calendar_service()
            now = datetime.utcnow().isoformat() + "Z"
            result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=kwargs.get("limit", 10),
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = result.get("items", [])
            formatted = []
            for e in events:
                start = e.get("start", {}).get("dateTime",
                       e.get("start", {}).get("date", ""))
                formatted.append({
                    "id": e.get("id"),
                    "title": e.get("summary", "No title"),
                    "start": start[:16] if start else "",
                    "attendees": [
                        a.get("email") for a in e.get("attendees", [])
                    ],
                    "description": e.get("description", "")
                })
            log.info("CalendarAgent got events", count=len(formatted))
            return {
                "action": "get_upcoming",
                "events": formatted,
                "count": len(formatted),
                "message": f"Found {len(formatted)} upcoming events"
            }
        except Exception as e:
            log.error("Calendar error", error=str(e))
            return {
                "action": "get_upcoming",
                "events": [],
                "count": 0,
                "message": f"Calendar error: {str(e)[:100]}"
            }

    elif action == "create_event":
        try:
            service = get_calendar_service()
            title = kwargs.get("title", "New Event")
            start_str = kwargs.get("start_time")
            end_str = kwargs.get("end_time")
            description = kwargs.get("description", "Created by ARIA")
            attendees = kwargs.get("attendees", [])

            if isinstance(start_str, str):
                start_dt = datetime.fromisoformat(start_str)
            else:
                start_dt = start_str or datetime.now() + timedelta(days=1)

            if isinstance(end_str, str):
                end_dt = datetime.fromisoformat(end_str)
            else:
                end_dt = end_str or start_dt + timedelta(hours=1)

            event_body = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "Asia/Kolkata"
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "Asia/Kolkata"
                },
                "attendees": [{"email": a} for a in attendees]
            }

            created = service.events().insert(
                calendarId="primary",
                body=event_body
            ).execute()

            log.info("Calendar event created", event_id=created.get("id"))
            return {
                "action": "create_event",
                "event_id": created.get("id"),
                "title": title,
                "start": str(start_dt)[:16],
                "link": created.get("htmlLink", ""),
                "message": f"Event '{title}' created for {str(start_dt)[:16]}"
            }
        except Exception as e:
            log.error("Calendar create error", error=str(e))
            return {
                "action": "create_event",
                "error": str(e),
                "message": f"Failed to create event: {str(e)[:100]}"
            }

    elif action == "suggest_schedule":
        try:
            # Get real calendar events
            service = get_calendar_service()
            now = datetime.utcnow().isoformat() + "Z"
            week_end = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

            result = service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=week_end,
                maxResults=20,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            existing_events = result.get("items", [])
            busy_times = []
            for e in existing_events:
                start = e.get("start", {}).get("dateTime", "")
                end = e.get("end", {}).get("dateTime", "")
                if start:
                    busy_times.append(f"- {e.get('summary', 'Busy')}: {start[:16]} to {end[:16]}")

            # Get pending tasks
            tasks = await queries.get_tasks(user_id=user_id, status="pending")
            if not tasks:
                return {
                    "action": "suggest_schedule",
                    "message": "No pending tasks to schedule",
                    "tasks_scheduled": 0
                }

            task_list = "\n".join([
                f"- [{t['priority'].upper()}] {t['title']} (due: {str(t.get('due_date', ''))[:10]})"
                for t in tasks[:15]
            ])

            busy_str = "\n".join(busy_times) if busy_times else "No existing events this week"

            response = client.models.generate_content(
                model=settings.gemini_flash_model,
                contents=f"""As ARIA's calendar assistant, create a specific schedule for this week.

Today: {datetime.now().strftime('%A, %B %d, %Y')}

Existing calendar events (AVOID these times):
{busy_str}

Tasks to schedule:
{task_list}

Create a day-by-day schedule for Mon-Fri with specific time slots.
Format each day clearly. Avoid conflicts with existing events.
Be specific: "Monday 9:00-11:00 AM: Define MVP Scope & Features"
""",
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=600
                )
            )

            return {
                "action": "suggest_schedule",
                "schedule": response.text.strip(),
                "tasks_scheduled": len(tasks),
                "existing_events": len(existing_events),
                "message": response.text.strip()
            }

        except Exception as e:
            log.error("Schedule error", error=str(e))
            return {
                "action": "suggest_schedule",
                "message": f"Schedule error: {str(e)[:100]}",
                "tasks_scheduled": 0
            }

    elif action == "check_conflicts":
        try:
            service = get_calendar_service()
            now = datetime.utcnow().isoformat() + "Z"
            tomorrow = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"

            result = service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=tomorrow,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = result.get("items", [])
            conflicts = []

            for i in range(len(events) - 1):
                e1_end = events[i].get("end", {}).get("dateTime", "")
                e2_start = events[i+1].get("start", {}).get("dateTime", "")
                if e1_end and e2_start and e1_end > e2_start:
                    conflicts.append({
                        "event1": events[i].get("summary", "Event 1"),
                        "event2": events[i+1].get("summary", "Event 2"),
                        "conflict_time": e2_start[:16]
                    })

            return {
                "action": "check_conflicts",
                "conflicts": conflicts,
                "count": len(conflicts),
                "message": f"Found {len(conflicts)} conflicts" if conflicts else "No conflicts detected"
            }
        except Exception as e:
            return {
                "action": "check_conflicts",
                "conflicts": [],
                "count": 0,
                "message": f"Error: {str(e)[:100]}"
            }

    else:
        return {
            "action": action,
            "error": f"Unknown action: {action}"
        }