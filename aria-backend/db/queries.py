import json
import structlog
from datetime import datetime
from db.client import execute, fetch_one, fetch_all, fetch_val

log = structlog.get_logger()


# ─────────────────────────────────────────────────────────
# USER QUERIES
# ─────────────────────────────────────────────────────────

async def get_user(user_id: str) -> dict | None:
    return await fetch_one(
        "SELECT * FROM aria_users WHERE id = $1", user_id
    )


async def get_user_by_email(email: str) -> dict | None:
    return await fetch_one(
        "SELECT * FROM aria_users WHERE email = $1", email
    )


async def update_user_preferences(user_id: str, preferences: dict):
    await execute(
        "UPDATE aria_users SET preferences = $1, updated_at = NOW() WHERE id = $2",
        json.dumps(preferences), user_id
    )


# ─────────────────────────────────────────────────────────
# PLAN QUERIES
# ─────────────────────────────────────────────────────────

async def create_plan(user_id: str, goal_text: str, milestones: list,
                      deadline: datetime | None = None, owner: str | None = None) -> dict:
    row = await fetch_one("""
        INSERT INTO plans (user_id, goal_text, milestones, deadline, owner, status)
        VALUES ($1, $2, $3::jsonb, $4, $5, 'active')
        RETURNING *
    """, user_id, goal_text, json.dumps(milestones), deadline, owner)
    log.info("Plan created", plan_id=row["id"], goal=goal_text[:50])
    return row


async def get_plans(user_id: str, status: str = "active") -> list[dict]:
    return await fetch_all(
        "SELECT * FROM plans WHERE user_id = $1 AND status = $2 ORDER BY created_at DESC",
        user_id, status
    )


async def get_plan(plan_id: str) -> dict | None:
    return await fetch_one("SELECT * FROM plans WHERE id = $1", plan_id)


async def update_plan_status(plan_id: str, status: str):
    await execute(
        "UPDATE plans SET status = $1, updated_at = NOW() WHERE id = $2",
        status, plan_id
    )


# ─────────────────────────────────────────────────────────
# TASK QUERIES
# ─────────────────────────────────────────────────────────

async def create_task(user_id: str, title: str, description: str = "",
                      priority: str = "medium", due_date: datetime | None = None,
                      plan_id: str | None = None, milestone: str | None = None,
                      assigned_to: str | None = None) -> dict:
    row = await fetch_one("""
        INSERT INTO tasks (user_id, plan_id, title, description, priority,
                          due_date, milestone, assigned_to, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
        RETURNING *
    """, user_id, plan_id, title, description, priority,
        due_date, milestone, assigned_to)
    log.info("Task created", task_id=row["id"], title=title)
    return row


async def get_tasks(user_id: str, status: str | None = None,
                    priority: str | None = None) -> list[dict]:
    if status and priority:
        return await fetch_all("""
            SELECT * FROM tasks WHERE user_id = $1
            AND status = $2 AND priority = $3
            ORDER BY due_date ASC NULLS LAST
        """, user_id, status, priority)
    elif status:
        return await fetch_all("""
            SELECT * FROM tasks WHERE user_id = $1 AND status = $2
            ORDER BY due_date ASC NULLS LAST
        """, user_id, status)
    else:
        return await fetch_all("""
            SELECT * FROM tasks WHERE user_id = $1
            ORDER BY due_date ASC NULLS LAST
        """, user_id)


async def get_task(task_id: str) -> dict | None:
    return await fetch_one("SELECT * FROM tasks WHERE id = $1", task_id)


async def update_task_status(task_id: str, status: str):
    await execute(
        "UPDATE tasks SET status = $1, updated_at = NOW() WHERE id = $2",
        status, task_id
    )


async def get_overdue_tasks(user_id: str) -> list[dict]:
    return await fetch_all("""
        SELECT * FROM tasks
        WHERE user_id = $1
        AND status NOT IN ('completed', 'cancelled')
        AND due_date < NOW()
        ORDER BY due_date ASC
    """, user_id)


async def get_tasks_by_plan(plan_id: str) -> list[dict]:
    return await fetch_all(
        "SELECT * FROM tasks WHERE plan_id = $1 ORDER BY due_date ASC NULLS LAST",
        plan_id
    )


# ─────────────────────────────────────────────────────────
# EVENT QUERIES
# ─────────────────────────────────────────────────────────

async def create_event(user_id: str, title: str, start_time: datetime,
                       end_time: datetime, description: str = "",
                       attendees: list | None = None, gcal_event_id: str | None = None,
                       location: str | None = None, plan_id: str | None = None) -> dict:
    row = await fetch_one("""
        INSERT INTO events (user_id, plan_id, title, description, start_time,
                           end_time, attendees, gcal_event_id, location)
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
        RETURNING *
    """, user_id, plan_id, title, description, start_time,
        end_time, json.dumps(attendees or []), gcal_event_id, location)
    log.info("Event created", event_id=row["id"], title=title)
    return row


async def get_upcoming_events(user_id: str, limit: int = 10) -> list[dict]:
    return await fetch_all("""
        SELECT * FROM events
        WHERE user_id = $1 AND start_time > NOW()
        ORDER BY start_time ASC
        LIMIT $2
    """, user_id, limit)


async def get_conflicting_events(user_id: str) -> list[dict]:
    return await fetch_all("""
        SELECT * FROM events
        WHERE user_id = $1 AND conflict_flag = TRUE
        AND start_time > NOW()
        ORDER BY start_time ASC
    """, user_id)


async def flag_event_conflict(event_id: str, conflict_details: dict):
    await execute("""
        UPDATE events SET conflict_flag = TRUE,
        conflict_details = $1::jsonb, updated_at = NOW()
        WHERE id = $2
    """, json.dumps(conflict_details), event_id)


# ─────────────────────────────────────────────────────────
# MEMORY QUERIES
# ─────────────────────────────────────────────────────────

async def save_memory(user_id: str, content: str, session_id: str,
                      summary: str = "", tags: list | None = None,
                      importance: str = "normal",
                      memory_type: str = "decision") -> dict:
    row = await fetch_one("""
        INSERT INTO memories (user_id, session_id, content, summary,
                             tags, importance, memory_type)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
        RETURNING *
    """, user_id, session_id, content, summary,
        json.dumps(tags or []), importance, memory_type)
    log.info("Memory saved", memory_id=row["id"], type=memory_type)
    return row


async def get_recent_memories(user_id: str, limit: int = 10) -> list[dict]:
    return await fetch_all("""
        SELECT * FROM memories
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, user_id, limit)


async def get_memories_by_type(user_id: str, memory_type: str) -> list[dict]:
    return await fetch_all("""
        SELECT * FROM memories
        WHERE user_id = $1 AND memory_type = $2
        ORDER BY created_at DESC
    """, user_id, memory_type)


# ─────────────────────────────────────────────────────────
# WATCH TRIGGER QUERIES
# ─────────────────────────────────────────────────────────

async def get_active_triggers(user_id: str) -> list[dict]:
    return await fetch_all("""
        SELECT * FROM watch_triggers
        WHERE user_id = $1 AND enabled = TRUE
        ORDER BY created_at ASC
    """, user_id)


async def update_trigger_fired(trigger_id: str):
    await execute("""
        UPDATE watch_triggers
        SET last_fired = NOW(), fire_count = fire_count + 1, updated_at = NOW()
        WHERE id = $1
    """, trigger_id)


async def get_all_active_triggers() -> list[dict]:
    """Used by WatchAgent to poll all users' triggers."""
    return await fetch_all("""
        SELECT * FROM watch_triggers
        WHERE enabled = TRUE
        ORDER BY user_id, trigger_type
    """)