import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from datetime import datetime
from db import queries
from db.client import get_pool

mcp = FastMCP("ARIA Task Manager")


@mcp.tool()
async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: str = None,
    plan_id: str = None,
    milestone: str = None,
    assigned_to: str = None,
    user_id: str = "user-aadarsh-001"
) -> dict:
    """Create a new task and store it in AlloyDB."""
    await get_pool()
    due = datetime.fromisoformat(due_date) if due_date else None
    task = await queries.create_task(
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due,
        plan_id=plan_id,
        milestone=milestone,
        assigned_to=assigned_to
    )
    return {
        "success": True,
        "task_id": task["id"],
        "title": title,
        "message": f"Task '{title}' created successfully"
    }


@mcp.tool()
async def get_all_tasks(
    user_id: str = "user-aadarsh-001",
    status: str = None,
    priority: str = None
) -> dict:
    """Get all tasks for a user."""
    await get_pool()
    tasks = await queries.get_tasks(
        user_id=user_id,
        status=status,
        priority=priority
    )
    return {
        "success": True,
        "count": len(tasks),
        "tasks": [
            {
                "id": t["id"],
                "title": t["title"],
                "priority": t["priority"],
                "status": t["status"],
                "due_date": str(t["due_date"])[:10] if t.get("due_date") else None,
                "milestone": t.get("milestone")
            }
            for t in tasks
        ]
    }


@mcp.tool()
async def update_task(
    task_id: str,
    status: str
) -> dict:
    """Update task status."""
    await get_pool()
    valid = ["pending", "in_progress", "completed", "blocked", "cancelled"]
    if status not in valid:
        return {"success": False, "error": f"Status must be one of {valid}"}
    await queries.update_task_status(task_id=task_id, status=status)
    return {
        "success": True,
        "message": f"Task {task_id} updated to '{status}'"
    }


@mcp.tool()
async def get_overdue_tasks(user_id: str = "user-aadarsh-001") -> dict:
    """Get all overdue tasks."""
    await get_pool()
    tasks = await queries.get_overdue_tasks(user_id=user_id)
    return {
        "success": True,
        "count": len(tasks),
        "tasks": [
            {
                "id": t["id"],
                "title": t["title"],
                "priority": t["priority"],
                "due_date": str(t["due_date"])[:10] if t.get("due_date") else None
            }
            for t in tasks
        ]
    }


@mcp.tool()
async def get_task_stats(user_id: str = "user-aadarsh-001") -> dict:
    """Get task statistics for a user."""
    await get_pool()
    all_tasks = await queries.get_tasks(user_id=user_id)
    pending = [t for t in all_tasks if t["status"] == "pending"]
    completed = [t for t in all_tasks if t["status"] == "completed"]
    in_progress = [t for t in all_tasks if t["status"] == "in_progress"]
    high_priority = [t for t in all_tasks if t["priority"] == "high"]

    return {
        "success": True,
        "total": len(all_tasks),
        "pending": len(pending),
        "completed": len(completed),
        "in_progress": len(in_progress),
        "high_priority": len(high_priority),
        "completion_rate": round(len(completed) / len(all_tasks) * 100) if all_tasks else 0
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)