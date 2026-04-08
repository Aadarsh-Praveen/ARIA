import asyncio
import uvicorn
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from config import settings
from db.client import get_pool, close_pool
from agents.orchestrator import run_orchestrator
from agents.watch import run_watch_agent, start_watch_loop, stop_watch_loop

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_pool()
    log.info("✅ ARIA Backend started")
    asyncio.create_task(start_watch_loop(interval=300))
    yield
    # Shutdown
    stop_watch_loop()
    await close_pool()
    log.info("ARIA Backend stopped")


app = FastAPI(
    title="ARIA — Adaptive Role-based Intelligence Assistant",
    description="Multi-agent AI productivity system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "user-aadarsh-001"
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    agent_actions: list
    session_id: str


@app.get("/")
async def root():
    return {
        "name": "ARIA",
        "status": "running",
        "version": "1.0.0",
        "message": "Adaptive Role-based Intelligence Assistant"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aria-backend"}


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        result = await run_orchestrator(
            user_message=request.message,
            user_id=request.user_id,
            session_id=request.session_id
        )
        return result
    except Exception as e:
        log.error("Chat error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/watch/trigger")
async def trigger_watch(user_id: str = "user-aadarsh-001"):
    try:
        results = await run_watch_agent(user_id=user_id)
        return {
            "triggered": len(results),
            "results": results,
            "message": f"{len(results)} trigger(s) fired" if results else "No triggers fired"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{user_id}")
async def get_status(user_id: str = "user-aadarsh-001"):
    from db.queries import get_plans, get_tasks, get_recent_memories
    plans = await get_plans(user_id=user_id)
    tasks = await get_tasks(user_id=user_id)
    memories = await get_recent_memories(user_id=user_id, limit=5)
    pending = [t for t in tasks if t["status"] == "pending"]
    completed = [t for t in tasks if t["status"] == "completed"]
    return {
        "user_id": user_id,
        "active_plans": len(plans),
        "total_tasks": len(tasks),
        "pending_tasks": len(pending),
        "completed_tasks": len(completed),
        "recent_memories": len(memories),
        "plans": [{"id": p["id"], "goal": p["goal_text"][:50]} for p in plans[:3]]
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )