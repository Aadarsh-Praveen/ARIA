import json
import structlog
from google import genai
from google.genai import types
from config import settings
from agents.planner import run_planner_agent
from agents.task import run_task_agent
from agents.memory import run_memory_agent
from agents.communication import run_communication_agent
from agents.watch import run_watch_agent

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)


async def route_message(message: str) -> list[str]:
    """Embedding-based intent classification — accurate and flexible."""
    try:
        from agents.router import classify_intent
        agents = await classify_intent(message)
        log.info("Embedding routing", message=message[:40], agents=agents)
        return agents
    except Exception as e:
        log.error("Embedding routing failed, using fallback", error=str(e))
        # Fallback to simple keyword check
        msg = message.lower()
        if any(k in msg for k in ["slack", "notify", "send", "tell team", "message team"]):
            return ["communication_draft"]
        if any(k in msg for k in ["decide", "decided", "pricing", "remember", "recall"]):
            return ["memory_recall"]
        if any(k in msg for k in ["urgent", "conflict", "overdue", "alert"]):
            return ["watch", "task_get"]
        return ["task_get"]

def build_detailed_context(results: dict) -> str:
    ctx = ""

    if "tasks" in results:
        task_list = results["tasks"].get("tasks", [])
        if task_list:
            ctx += f"\n\nHere are ALL {len(task_list)} tasks:\n"
            for i, t in enumerate(task_list, 1):
                due = t.get("due_date", "No due date")
                priority = t.get("priority", "medium").upper()
                status = t.get("status", "pending")
                milestone = t.get("milestone", "")
                ctx += f"{i}. [{priority}] {t['title']}\n"
                ctx += f"   Due: {due} | Status: {status}"
                if milestone:
                    ctx += f" | Milestone: {milestone}"
                ctx += "\n"

    if "planner" in results:
        plan = results["planner"]
        ctx += f"\n\nNew plan created: '{plan.get('plan_title', '')}'"
        ctx += f"\nDeadline: {str(plan.get('deadline', ''))[:10]}"
        ctx += f"\nTotal milestones: {plan.get('milestones_count', 0)}"
        ctx += f"\nTotal tasks created: {plan.get('tasks_count', 0)}"
        ctx += "\n\nMilestones:"
        for m in plan.get("milestones", []):
            ctx += f"\n  - {m['name']} (due day {m.get('due_day', '?')})"
        ctx += "\n\nFirst 10 tasks created:"
        for t in plan.get("tasks", [])[:10]:
            ctx += f"\n  - [{t['priority'].upper()}] {t['title']}"
        remaining = plan.get("tasks_count", 0) - 10
        if remaining > 0:
            ctx += f"\n  ... and {remaining} more tasks"

    if "memory" in results:
        answer = results["memory"].get("answer", "")
        searched = results["memory"].get("memories_searched", 0)
        source = results["memory"].get("source", "memory")
        if answer:
            ctx += f"\n\nRecalled from {source} ({searched} memories searched):\n{answer}"
        else:
            ctx += "\n\nNo relevant past decisions found."

    if "task_summary" in results:
        summary = results["task_summary"]
        ctx += f"\n\nTask summary: {summary.get('summary', '')}"
        ctx += f"\nStats: {summary.get('total', 0)} total"
        ctx += f", {summary.get('pending', 0)} pending"
        ctx += f", {summary.get('completed', 0)} completed"
        ctx += f", {summary.get('high_priority', 0)} high priority"

    if "watch" in results:
        triggers = results["watch"]
        if triggers:
            ctx += f"\n\n⚠️ URGENT ALERTS ({len(triggers)}):"
            for trigger in triggers:
                ctx += f"\n- {trigger.get('message', '')}"
                for t in trigger.get("urgent_tasks", []):
                    ctx += f"\n  * {t['title']} (due: {str(t.get('due_date', ''))[:10]})"
        else:
            ctx += "\n\nNo urgent issues. Everything is on track."

    if "calendar" in results:
        schedule = results["calendar"].get("schedule", "")
        tasks_scheduled = results["calendar"].get("tasks_scheduled", 0)
        if schedule:
            ctx += f"\n\nSuggested schedule ({tasks_scheduled} tasks):\n{schedule}"

    if "communication" in results:
        draft = results["communication"].get("draft", "")
        sent = results["communication"].get("sent", False)
        if draft:
            status = "SENT to Slack ✅" if sent else "Drafted"
            ctx += f"\n\nSlack message [{status}]:\n---\n{draft}\n---"

    return ctx


async def run_orchestrator(
    user_message: str,
    user_id: str = "user-aadarsh-001",
    session_id: str = "default"
) -> dict:
    log.info("OrchestratorAgent started", message=user_message[:50])

    # Step 1: Load memory context
    try:
        context_result = await run_memory_agent(
            "load_context", user_id=user_id, session_id=session_id
        )
        memory_context = context_result.get("context", {})
    except Exception as e:
        log.error("Memory load error", error=str(e))
        memory_context = {}

    # Step 2: Route message
    agents_to_call = await route_message(user_message)
    log.info("Routing decision", agents=agents_to_call)

    # Step 3: Execute agents
    results = {}
    agent_actions = []

    for agent in agents_to_call:
        try:
            if agent == "planner":
                result = await run_planner_agent(
                    goal=user_message,
                    user_id=user_id
                )
                results["planner"] = result
                agent_actions.append({
                    "agent": "PlannerAgent",
                    "status": "success",
                    "summary": f"Created plan '{result.get('plan_title', '')}' with {result['milestones_count']} milestones and {result['tasks_count']} tasks"
                })

            elif agent == "task_get":
                result = await run_task_agent("get_tasks", user_id=user_id)
                results["tasks"] = result
                agent_actions.append({
                    "agent": "TaskAgent",
                    "status": "success",
                    "summary": f"Retrieved {result['count']} tasks from database"
                })

            elif agent == "task_summarize":
                result = await run_task_agent("summarize", user_id=user_id)
                results["task_summary"] = result
                agent_actions.append({
                    "agent": "TaskAgent",
                    "status": "success",
                    "summary": "Summarized all tasks and progress"
                })

            elif agent == "memory_recall":
                result = await run_memory_agent(
                    "recall",
                    user_id=user_id,
                    session_id=session_id,
                    query=user_message
                )
                results["memory"] = result
                agent_actions.append({
                    "agent": "MemoryAgent",
                    "status": "success",
                    "summary": f"Recalled from {result.get('source', 'memory')} — {result.get('memories_searched', 0)} memories searched"
                })

            elif agent == "communication_draft":
                # Get task context to include in message
                task_context = ""
                if "tasks" not in results:
                    task_result = await run_task_agent("get_tasks", user_id=user_id)
                    results["tasks"] = task_result
                    task_list = task_result.get("tasks", [])
                    task_context = "\n".join([
                        f"{i+1}. [{t['priority'].upper()}] {t['title']} — Due: {t.get('due_date', 'TBD')}"
                        for i, t in enumerate(task_list[:15])
                    ])

                context_str = f"User request: {user_message}\n\nCurrent tasks:\n{task_context}" if task_context else user_message

                # Always send to Slack when communication agent is triggered
                result = await run_communication_agent(
                    "draft_and_send",
                    user_id=user_id,
                    context=context_str,
                    purpose=f"Team update: {user_message}"
                )
                results["communication"] = result
                agent_actions.append({
                    "agent": "CommunicationAgent",
                    "status": "success",
                    "summary": "✅ Slack message sent to team!"
                })

            elif agent == "calendar_schedule":
                from agents.calendar import run_calendar_agent
                result = await run_calendar_agent(
                    "suggest_schedule",
                    user_id=user_id
                )
                results["calendar"] = result
                agent_actions.append({
                    "agent": "CalendarAgent",
                    "status": "success",
                    "summary": f"Suggested schedule for {result.get('tasks_scheduled', 0)} tasks"
                })

            elif agent == "watch":
                triggered = await run_watch_agent(user_id=user_id)
                results["watch"] = triggered
                if triggered:
                    agent_actions.append({
                        "agent": "WatchAgent",
                        "status": "triggered",
                        "summary": f"{len(triggered)} urgent trigger(s) fired"
                    })
                else:
                    agent_actions.append({
                        "agent": "WatchAgent",
                        "status": "success",
                        "summary": "No urgent issues found"
                    })

        except Exception as e:
            log.error("Agent error", agent=agent, error=str(e))
            agent_actions.append({
                "agent": agent,
                "status": "error",
                "summary": f"Error: {str(e)[:100]}"
            })

    # Step 4: Save to memory
    try:
        await run_memory_agent(
            "save",
            user_id=user_id,
            session_id=session_id,
            content=f"User asked: '{user_message}'. Actions: {[a['summary'] for a in agent_actions]}",
            memory_type="context",
            importance="normal"
        )
    except Exception as e:
        log.error("Memory save error", error=str(e))

    # Step 5: Build context and generate response
    detailed_context = build_detailed_context(results)
    results_summary = "\n".join([
        f"- {a['agent']}: {a['summary']}" for a in agent_actions
    ])

    final_prompt = f"""You are ARIA, a friendly and highly capable AI chief of staff.

User said: "{user_message}"

What your agents did:
{results_summary}

Complete data retrieved:
{detailed_context}

CRITICAL RULES:
1. TASKS: If user asked to list tasks → show ALL tasks numbered:
   1. [HIGH] Task name — Due: date — Milestone: name
   Never skip any task.

2. PLANNING: If plan created → mention title, all milestones, task count, deadline.

3. MEMORY: Give EXACT recalled answer with numbers and dates.
   If nothing found → "I don't have a record of that yet."

4. SLACK SENT: If CommunicationAgent sent a message → confirm it was sent
   and show the full message content clearly.

5. URGENT: If WatchAgent found issues → highlight with ⚠️.

6. SCHEDULE: Show the full suggested schedule.

7. Always be specific. Use actual data. Never be vague.
8. Be friendly and well-formatted.
"""

    final_response = client.models.generate_content(
        model=settings.gemini_flash_model,
        contents=final_prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2000
        )
    )

    response_text = final_response.text.strip()
    log.info("OrchestratorAgent done", response=response_text[:100])

    return {
        "response": response_text,
        "agent_actions": agent_actions,
        "session_id": session_id,
        "user_id": user_id,
        "results": results
    }