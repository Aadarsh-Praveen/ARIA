import json
import structlog
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from config import settings
from db import queries

log = structlog.get_logger()

client = genai.Client(api_key=settings.gemini_api_key)


async def run_planner_agent(goal: str, user_id: str = "user-aadarsh-001") -> dict:
    log.info("PlannerAgent started", goal=goal[:50])

    prompt = f"""
You are a world-class project planner. A user has given you this goal:

"{goal}"

Break this down into a realistic project plan. Return ONLY valid JSON with this exact structure:
{{
    "plan_title": "short title for the plan",
    "deadline_days": 21,
    "milestones": [
        {{
            "name": "milestone name",
            "description": "what this milestone achieves",
            "due_day": 7,
            "tasks": [
                {{
                    "title": "task title",
                    "description": "what needs to be done",
                    "priority": "high",
                    "estimated_hours": 2,
                    "due_day": 3
                }}
            ]
        }}
    ]
}}

Rules:
- Create 3-5 milestones
- Each milestone should have 3-5 tasks
- Be specific and actionable
- Return ONLY the JSON, no other text
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=4096,
        )
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    plan_data = json.loads(raw)
    log.info("Plan generated", milestones=len(plan_data["milestones"]))

    start_date = datetime.now()
    deadline = start_date + timedelta(days=plan_data["deadline_days"])

    milestones_summary = [
        {
            "name": m["name"],
            "description": m["description"],
            "due_day": m["due_day"]
        }
        for m in plan_data["milestones"]
    ]

    plan = await queries.create_plan(
        user_id=user_id,
        goal_text=goal,
        milestones=milestones_summary,
        deadline=deadline,
        owner="Aadarsh"
    )

    tasks_created = []
    for milestone in plan_data["milestones"]:
        for task in milestone["tasks"]:
            due = start_date + timedelta(days=task["due_day"])
            created_task = await queries.create_task(
                user_id=user_id,
                title=task["title"],
                description=task["description"],
                priority=task["priority"],
                due_date=due,
                plan_id=plan["id"],
                milestone=milestone["name"]
            )
            tasks_created.append(created_task)

    log.info("PlannerAgent done", plan_id=plan["id"], tasks=len(tasks_created))

    return {
        "plan_id": plan["id"],
        "plan_title": plan_data["plan_title"],
        "milestones_count": len(plan_data["milestones"]),
        "tasks_count": len(tasks_created),
        "deadline": deadline.isoformat(),
        "milestones": milestones_summary,
        "tasks": [
            {"id": t["id"], "title": t["title"], "priority": t["priority"]}
            for t in tasks_created
        ],
        "message": f"Created plan with {len(plan_data['milestones'])} milestones and {len(tasks_created)} tasks"
    }