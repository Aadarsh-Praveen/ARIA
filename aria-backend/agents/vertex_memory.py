import os
import structlog
from google.cloud.aiplatform_v1beta1.services.memory_bank_service import MemoryBankServiceClient
from google.cloud.aiplatform_v1beta1.types import memory_bank as mb_types
from google import genai
from google.genai import types
from config import settings

log = structlog.get_logger()

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_sa_path = os.path.join(_root, "service-account.json")
if not os.path.exists(_sa_path):
    _sa_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _sa_path

REASONING_ENGINE = "projects/629352210643/locations/us-central1/reasoningEngines/4973390709349416960"

client_mb = MemoryBankServiceClient(
    client_options={"api_endpoint": "us-central1-aiplatform.googleapis.com"}
)

client_gemini = genai.Client(api_key=settings.gemini_api_key)


async def save_to_vertex_memory(
    content: str,
    user_id: str = "user-aadarsh-001",
    memory_type: str = "decision"
) -> dict:
    """Save a memory to Vertex AI Memory Bank."""
    try:
        memory = mb_types.Memory()
        memory.fact = content
        memory.scope = {"user_id": user_id, "type": memory_type}

        client_mb.create_memory(
            parent=REASONING_ENGINE,
            memory=memory
        )
        log.info("Vertex AI memory saved", type=memory_type)
        return {
            "success": True,
            "message": "Saved to Vertex AI Memory Bank",
            "content": content[:50]
        }
    except Exception as e:
        log.error("Vertex memory save error", error=str(e))
        return {"success": False, "error": str(e)}


async def recall_from_vertex_memory(
    query: str,
    user_id: str = "user-aadarsh-001"
) -> dict:
    """Retrieve memories from Vertex AI Memory Bank."""
    try:
        memories = client_mb.list_memories(parent=REASONING_ENGINE)
        all_facts = []
        for m in memories:
            scope = dict(m.scope) if m.scope else {}
            if scope.get("user_id") == user_id or not scope:
                all_facts.append(m.fact)

        if not all_facts:
            return {
                "success": True,
                "answer": "No memories found in Vertex AI Memory Bank yet.",
                "memories_count": 0,
                "source": "Vertex AI Memory Bank"
            }

        facts_text = "\n".join([f"- {f}" for f in all_facts])

        response = client_gemini.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"""You are ARIA's Vertex AI Memory Bank system.

Stored memories:
{facts_text}

User query: {query}

Answer specifically using the memories above.
Be precise with numbers, dates, and decisions.
If not found, say: 'I don't have a record of that yet.'
""",
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=400
            )
        )

        log.info("Vertex AI memory recalled",
                 memories=len(all_facts), query=query[:40])
        return {
            "success": True,
            "answer": response.text.strip(),
            "memories_count": len(all_facts),
            "source": "Vertex AI Memory Bank"
        }
    except Exception as e:
        log.error("Vertex AI recall error", error=str(e))
        return {
            "success": False,
            "answer": "Memory recall error",
            "error": str(e),
            "source": "Vertex AI Memory Bank"
        }


async def seed_vertex_memories(user_id: str = "user-aadarsh-001"):
    """Seed initial memories into Vertex AI Memory Bank."""
    memories = [
        ("User decided to price the product at $49/month for individuals and $199/month for teams. Competitor benchmark was $39. Premium justified by analytics features.", "decision"),
        ("Team agreed to use React + FastAPI + AlloyDB as the core tech stack. Deployment target is Google Cloud Run.", "decision"),
        ("Product launch target date set for April 29, 2026. Marketing campaign starts April 22.", "decision"),
        ("User prefers morning meetings before 11am. Afternoons reserved for deep work and coding.", "preference"),
        ("Q1 revenue target is $50,000. Current pipeline shows 12 qualified leads.", "fact"),
        ("Team size: 4 engineers, 1 designer, 1 product manager. Budget: $200k for the year.", "fact"),
        ("Decided to integrate Slack and Gmail as primary communication channels. WhatsApp integration deferred to v2.", "decision"),
        ("ARIA system uses Gemini 2.5 Flash for sub-agents and Gemini 2.5 Pro for orchestration.", "fact"),
        ("AlloyDB instance aria-db running in us-central1 with pgvector for semantic search.", "fact"),
        ("WatchAgent polls every 5 minutes for deadline conflicts and urgent task alerts.", "fact"),
    ]

    saved = 0
    for content, mtype in memories:
        result = await save_to_vertex_memory(
            content=content,
            user_id=user_id,
            memory_type=mtype
        )
        if result["success"]:
            saved += 1
            log.info("Seeded memory", content=content[:50])

    log.info("Vertex AI memories seeded", count=saved)
    return {"seeded": saved, "total": len(memories)}