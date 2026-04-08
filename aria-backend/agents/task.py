import structlog
from datetime import datetime
from google import genai
from google.genai import types
from config import settings
from db import queries

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)


async def run_task_agent(
    action: str,
    user_id: str = "user-aadarsh-001",
    **kwargs
) -> dict:
    log.info("TaskAgent started", action=action)

    if action == "get_tasks":
        tasks = await queries.get_tasks(
            user_id=user_id,
            status=kwargs.get("status"),
            priority=kwargs.get("priority")
        )
        # Format tasks nicely
        formatted = []
        for t in tasks:
            formatted.append({
                "id": t["id"],
                "title": t["title"],
                "priority": t["priority"],
                "status": t["status"],
                "due_date": str(t["due_date"])[:10] if t.get("due_date") else "No due date",
                "milestone": t.get("milestone", ""),
                "description": t.get("description", "")
            })
        return {
            "action": "get_tasks",
            "tasks": formatted,
            "count": len(formatted),
            "message": f"Found {len(formatted)} tasks"
        }

    elif action == "create_task":
        due_date = None
        if kwargs.get("due_date"):
            try:
                due_date = datetime.fromisoformat(kwargs["due_date"])
            except Exception:
                due_date = None

        task = await queries.create_task(
            user_id=user_id,
            title=kwargs["title"],
            description=kwargs.get("description", ""),
            priority=kwargs.get("priority", "medium"),
            due_date=due_date,
            plan_id=kwargs.get("plan_id"),
            milestone=kwargs.get("milestone"),
            assigned_to=kwargs.get("assigned_to")
        )
        return {
            "action": "create_task",
            "task_id": task["id"],
            "title": task["title"],
            "message": f"Task '{kwargs['title']}' created successfully"
        }

    elif action == "update_status":
        task_id = kwargs.get("task_id")
        status = kwargs.get("status")
        if not task_id or not status:
            return {"action": "update_status", "error": "task_id and status required"}

        await queries.update_task_status(
            task_id=task_id,
            status=status
        )
        return {
            "action": "update_status",
            "task_id": task_id,
            "new_status": status,
            "message": f"Task updated to '{status}'"
        }

    elif action == "get_overdue":
        tasks = await queries.get_overdue_tasks(user_id=user_id)
        formatted = []
        for t in tasks:
            formatted.append({
                "id": t["id"],
                "title": t["title"],
                "priority": t["priority"],
                "due_date": str(t["due_date"])[:10] if t.get("due_date") else "No due date"
            })
        return {
            "action": "get_overdue",
            "tasks": formatted,
            "count": len(formatted),
            "message": f"Found {len(formatted)} overdue tasks"
        }

    elif action == "summarize":
        tasks = await queries.get_tasks(user_id=user_id)
        if not tasks:
            return {
                "action": "summarize",
                "summary": "No tasks found.",
                "message": "No tasks found."
            }

        pending = [t for t in tasks if t["status"] == "pending"]
        completed = [t for t in tasks if t["status"] == "completed"]
        in_progress = [t for t in tasks if t["status"] == "in_progress"]
        high = [t for t in tasks if t["priority"] == "high"]

        task_list = "\n".join([
            f"- [{t['priority'].upper()}] {t['title']} ({t['status']})"
            for t in tasks[:20]
        ])

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"""Summarize these tasks for a busy professional in 2-3 sentences.
Focus on what's most important and urgent:

{task_list}

Stats: {len(pending)} pending, {len(completed)} completed, {len(in_progress)} in progress, {len(high)} high priority""",
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=200
            )
        )

        return {
            "action": "summarize",
            "summary": response.text.strip(),
            "total": len(tasks),
            "pending": len(pending),
            "completed": len(completed),
            "in_progress": len(in_progress),
            "high_priority": len(high),
            "message": response.text.strip()
        }

    elif action == "get_stats":
        tasks = await queries.get_tasks(user_id=user_id)
        pending = len([t for t in tasks if t["status"] == "pending"])
        completed = len([t for t in tasks if t["status"] == "completed"])
        in_progress = len([t for t in tasks if t["status"] == "in_progress"])
        high = len([t for t in tasks if t["priority"] == "high"])
        rate = round(completed / len(tasks) * 100) if tasks else 0

        return {
            "action": "get_stats",
            "total": len(tasks),
            "pending": pending,
            "completed": completed,
            "in_progress": in_progress,
            "high_priority": high,
            "completion_rate": rate,
            "message": f"{len(tasks)} tasks total, {completed} done, {pending} pending"
        }

    else:
        return {
            "action": action,
            "error": f"Unknown action: {action}"
        }