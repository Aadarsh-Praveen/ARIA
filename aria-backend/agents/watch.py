import asyncio
import structlog
import json
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from config import settings
from db import queries

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)

_running = False


async def check_deadline_triggers(user_id: str, condition: dict) -> dict | None:
    hours_before = condition.get("hours_before", 48)
    priority_filter = condition.get("priority", ["high", "critical"])
    deadline = datetime.now() + timedelta(hours=hours_before)

    tasks = await queries.get_tasks(user_id=user_id)
    urgent = [
        t for t in tasks
        if t.get("due_date")
        and t["status"] not in ["completed", "cancelled"]
        and t["priority"] in priority_filter
        and datetime.fromisoformat(str(t["due_date"])).replace(tzinfo=None) <= deadline
    ]

    if urgent:
        return {
            "trigger_type": "deadline",
            "urgent_tasks": [
                {"id": t["id"], "title": t["title"], "due_date": str(t["due_date"])}
                for t in urgent
            ],
            "count": len(urgent),
            "message": f"⚠️ {len(urgent)} urgent task(s) due within {hours_before} hours!"
        }
    return None


async def check_conflict_triggers(user_id: str) -> dict | None:
    conflicting = await queries.get_conflicting_events(user_id=user_id)
    if conflicting:
        return {
            "trigger_type": "conflict",
            "conflicting_events": [
                {"id": e["id"], "title": e["title"]}
                for e in conflicting
            ],
            "count": len(conflicting),
            "message": f"⚠️ {len(conflicting)} calendar conflict(s) detected!"
        }
    return None


async def run_watch_agent(user_id: str = "user-aadarsh-001") -> list[dict]:
    log.info("WatchAgent polling", user_id=user_id)
    triggered = []

    triggers = await queries.get_active_triggers(user_id=user_id)

    for trigger in triggers:
        result = None
        trigger_type = trigger["trigger_type"]

        # ✅ FIX: handle condition_json as string or dict
        condition = trigger["condition_json"]
        if isinstance(condition, str):
            condition = json.loads(condition)

        # ✅ FIX: handle action_json as string or dict
        action = trigger["action_json"]
        if isinstance(action, str):
            action = json.loads(action)

        if trigger_type == "deadline":
            result = await check_deadline_triggers(user_id, condition)
        elif trigger_type == "conflict":
            result = await check_conflict_triggers(user_id)

        if result:
            await queries.update_trigger_fired(trigger["id"])
            result["trigger_name"] = trigger["trigger_name"]
            result["action"] = action
            triggered.append(result)
            log.info("WatchAgent trigger fired",
                     trigger=trigger["trigger_name"],
                     type=trigger_type)

    return triggered


async def start_watch_loop(user_id: str = "user-aadarsh-001", interval: int = 300):
    global _running
    _running = True
    log.info("WatchAgent loop started", interval_seconds=interval)

    while _running:
        try:
            results = await run_watch_agent(user_id=user_id)
            if results:
                log.info("WatchAgent fired triggers", count=len(results))
        except Exception as e:
            log.error("WatchAgent error", error=str(e))
        await asyncio.sleep(interval)


def stop_watch_loop():
    global _running
    _running = False
    log.info("WatchAgent loop stopped")