import numpy as np
from google import genai
from config import settings
import structlog

log = structlog.get_logger()
client = genai.Client(api_key=settings.gemini_api_key)

# Intent definitions with example phrases
INTENT_EXAMPLES = {
    "communication_draft": [
        "notify the team", "send a slack message", "tell the team",
        "message the team", "send this to the team", "update the team",
        "inform the team", "share this with everyone", "post an update",
        "draft a message", "let everyone know", "send update to team",
        "notify slack", "send to slack", "communicate to team",
        "send this", "share this", "pass this along"
    ],
    "memory_recall": [
        "what did we decide", "what was decided", "do you remember",
        "recall our decision", "what was our pricing", "what is our budget",
        "what did we agree on", "tell me about our past decisions",
        "what is our tech stack", "what was discussed", "history",
        "previous session", "last week we decided", "stored memory"
    ],
    "task_get": [
        "list my tasks", "show me my tasks", "what are my tasks",
        "what do I need to do", "my pending tasks", "show all tasks",
        "what tasks do I have", "display my tasks", "get my tasks",
        "fetch tasks", "retrieve tasks", "all tasks"
    ],
    "task_summarize": [
        "summarize my progress", "how am I doing", "give me an overview",
        "progress report", "brief me", "catch me up", "status update",
        "how many tasks done", "completion rate", "summary of work"
    ],
    "planner": [
        "create a plan", "make a roadmap", "plan this project",
        "break this down", "help me organize", "create milestones",
        "plan my launch", "build a strategy", "project planning",
        "make a schedule for project"
    ],
    "calendar_schedule": [
        "schedule my week", "plan my day", "book a meeting",
        "what's on my calendar", "create an event", "block time",
        "schedule tasks", "time management", "calendar view",
        "when should I work on"
    ],
    "watch": [
        "check for urgent issues", "any conflicts", "what's overdue",
        "deadline alerts", "proactive check", "what's at risk",
        "any blocked tasks", "urgent items", "what needs attention now",
        "check conflicts"
    ]
}

# Cache embeddings at startup
_intent_embeddings = {}


async def get_embedding(text: str) -> list[float]:
    """Get text embedding using available Gemini embedding model."""
    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        log.error("Embedding error", error=str(e))
        return []


def cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity."""
    a, b = np.array(a), np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def build_intent_embeddings():
    """Pre-compute embeddings for all intent examples."""
    global _intent_embeddings
    if _intent_embeddings:
        return

    log.info("Building intent embeddings...")
    for intent, examples in INTENT_EXAMPLES.items():
        embeddings = []
        for example in examples:
            emb = await get_embedding(example)
            if emb:
                embeddings.append(emb)
        _intent_embeddings[intent] = embeddings
    log.info("Intent embeddings built", intents=list(_intent_embeddings.keys()))


async def classify_intent(message: str) -> list[str]:
    """Classify user message intent using embeddings."""
    global _intent_embeddings

    # Build embeddings if not cached
    if not _intent_embeddings:
        await build_intent_embeddings()

    # Get message embedding
    msg_embedding = await get_embedding(message)
    if not msg_embedding:
        return ["task_get"]

    # Calculate similarity to each intent
    scores = {}
    for intent, embeddings in _intent_embeddings.items():
        if embeddings:
            sims = [cosine_similarity(msg_embedding, emb) for emb in embeddings]
            scores[intent] = max(sims)

    # Sort by score
    sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    log.info("Intent scores", message=message[:40],
             top3=[(k, round(v, 3)) for k, v in sorted_intents[:3]])

    # Get top intent
    top_intent = sorted_intents[0][0]
    top_score = sorted_intents[0][1]

    # If score is very low, default to task_get
    if top_score < 0.5:
        return ["task_get"]

    # Special combinations
    if top_intent == "watch":
        return ["watch", "task_get"]
    if top_intent == "calendar_schedule":
        return ["calendar_schedule", "task_get"]
    if top_intent == "task_summarize" and sorted_intents[1][0] == "watch":
        return ["task_summarize", "watch"]

    return [top_intent]