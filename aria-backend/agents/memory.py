import structlog
from google import genai
from google.genai import types
from config import settings
from db import queries

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)


async def run_memory_agent(
    action: str,
    user_id: str = "user-aadarsh-001",
    session_id: str = "default",
    **kwargs
) -> dict:
    log.info("MemoryAgent started", action=action)

    if action == "save":
        content = kwargs.get("content", "")
        memory_type = kwargs.get("memory_type", "decision")
        importance = kwargs.get("importance", "normal")

        # Generate summary
        try:
            response = client.models.generate_content(
                model=settings.gemini_flash_model,
                contents=f"Summarize in one sentence: {content}",
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=100
                )
            )
            summary = response.text.strip()
        except Exception:
            summary = content[:100]

        # Save to local AlloyDB
        memory = await queries.save_memory(
            user_id=user_id,
            content=content,
            session_id=session_id,
            summary=summary,
            tags=kwargs.get("tags", []),
            importance=importance,
            memory_type=memory_type
        )

        # Also save to Vertex AI Memory Bank
        try:
            from agents.vertex_memory import save_to_vertex_memory
            await save_to_vertex_memory(
                content=content,
                user_id=user_id,
                memory_type=memory_type
            )
            storage = "AlloyDB + Vertex AI Memory Bank"
            log.info("Saved to both AlloyDB and Vertex AI Memory Bank")
        except Exception as e:
            storage = "AlloyDB"
            log.error("Vertex AI save failed, saved to AlloyDB only", error=str(e))

        log.info("Memory saved", memory_id=memory["id"], type=memory_type)
        return {
            "action": "save",
            "memory_id": memory["id"],
            "summary": summary,
            "storage": storage,
            "message": f"Memory saved to {storage}"
        }

    elif action == "recall":
        query = kwargs.get("query", "")
        log.info("Memory recall started", query=query[:50])

        # Try Vertex AI Memory Bank first
        try:
            from agents.vertex_memory import recall_from_vertex_memory
            vertex_result = await recall_from_vertex_memory(
                query=query,
                user_id=user_id
            )
            if (vertex_result["success"] and
                    vertex_result["memories_count"] > 0 and
                    "don't have a record" not in vertex_result["answer"]):
                log.info("Vertex AI Memory Bank recall success",
                         count=vertex_result["memories_count"])
                return {
                    "action": "recall",
                    "answer": vertex_result["answer"],
                    "memories_searched": vertex_result["memories_count"],
                    "source": "Vertex AI Memory Bank",
                    "message": vertex_result["answer"]
                }
        except Exception as e:
            log.error("Vertex AI recall failed, falling back to AlloyDB",
                      error=str(e))

        # Fallback to AlloyDB
        log.info("Using AlloyDB memory fallback")
        all_memories = await queries.get_recent_memories(
            user_id=user_id, limit=50
        )
        decisions = await queries.get_memories_by_type(
            user_id=user_id, memory_type="decision"
        )
        facts = await queries.get_memories_by_type(
            user_id=user_id, memory_type="fact"
        )
        preferences = await queries.get_memories_by_type(
            user_id=user_id, memory_type="preference"
        )

        seen_ids = set()
        combined = []
        for m in (decisions + facts + preferences + all_memories):
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                combined.append(m)

        if not combined:
            return {
                "action": "recall",
                "answer": "I don't have any memories stored yet.",
                "memories_searched": 0,
                "source": "AlloyDB",
                "message": "No memories found"
            }

        memory_text = "\n".join([
            f"[{m['memory_type'].upper()}] {m['content']}"
            for m in combined
        ])

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"""You are ARIA's memory system.

Stored memories:
{memory_text}

Question: {query}

Answer specifically. Use exact numbers and dates.
If not found say: 'I don't have a record of that yet.'
""",
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=500
            )
        )

        return {
            "action": "recall",
            "answer": response.text.strip(),
            "memories_searched": len(combined),
            "source": "AlloyDB Memory",
            "message": response.text.strip()
        }

    elif action == "get_recent":
        memories = await queries.get_recent_memories(
            user_id=user_id,
            limit=kwargs.get("limit", 5)
        )
        return {
            "action": "get_recent",
            "memories": memories,
            "count": len(memories),
            "message": f"Found {len(memories)} recent memories"
        }

    elif action == "load_context":
        memories = await queries.get_recent_memories(
            user_id=user_id, limit=20
        )
        plans = await queries.get_plans(user_id=user_id)
        tasks = await queries.get_tasks(
            user_id=user_id, status="pending"
        )

        context = {
            "recent_memories": [
                m["summary"] or m["content"]
                for m in memories[:5]
            ],
            "active_plans": [p["goal_text"] for p in plans[:3]],
            "pending_tasks_count": len(tasks),
            "user_id": user_id,
            "session_id": session_id
        }

        return {
            "action": "load_context",
            "context": context,
            "message": "Context loaded successfully"
        }

    else:
        return {
            "action": action,
            "error": f"Unknown action: {action}"
        }