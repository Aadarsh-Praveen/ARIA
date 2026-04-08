# ARIA — Adaptive Role-based Intelligence Assistant

## Track: Multi-Agent Productivity Assistant

ARIA is a self-organizing multi-agent AI system where an OrchestratorAgent powered by Gemini 2.5 Pro coordinates 6 specialized sub-agents to manage tasks, schedules, and information autonomously across Slack, Google Calendar, and a custom AlloyDB-backed task system. It learns from every session via Vertex AI Memory Bank and acts proactively without being prompted.

---

## Demo Video

Watch the 3-minute demo: YOUR_YOUTUBE_URL_HERE

## Live Demo

Try ARIA live: https://aria-frontend-629352210643.us-central1.run.app

---

## What Makes ARIA Different

| Feature | Other Submissions | ARIA |
|---|---|---|
| Memory | Resets every session | Persistent via Vertex AI Memory Bank |
| Behavior | Reactive only | Proactive — WatchAgent fires autonomously |
| Database | Simple key-value | AlloyDB + pgvector semantic search |
| Integrations | Simulated | Real Google Calendar + Real Slack |
| MCP | None or basic | Custom Task MCP Server + 3 integrations |
| Demo scope | Add a task | Full project launch in 60 seconds |

---

## Architecture

The system follows this request flow:

User sends a message to the FastAPI backend deployed on Cloud Run. The OrchestratorAgent powered by Gemini 2.5 Pro receives the request, loads context from Vertex AI Memory Bank, and routes to the appropriate sub-agents. Each sub-agent executes its task using real tool integrations — Google Calendar API, Slack SDK, AlloyDB, and the custom Task MCP Server. Results are aggregated and returned to the user. The WatchAgent runs independently on a 5-minute polling loop, firing proactive workflows without any user input.

---

## The 6 Agents

| Agent | Model | Role |
|---|---|---|
| OrchestratorAgent | Gemini 2.5 Pro | Receives user intent, routes to sub-agents, aggregates results |
| PlannerAgent | Gemini 2.5 Flash | Breaks goals into milestones and tasks, writes to AlloyDB |
| CalendarAgent | Gemini 2.5 Flash | Real Google Calendar — creates events, detects conflicts, suggests schedules |
| TaskAgent | Gemini 2.5 Flash | Full task CRUD via custom FastMCP server backed by AlloyDB |
| MemoryAgent | Gemini 2.5 Flash | Vertex AI Memory Bank + AlloyDB for cross-session recall |
| WatchAgent | Gemini 2.5 Flash | Proactive monitoring — fires autonomously without user prompt |

---

## Live Workflows

### Workflow 1 — Project Launch (60 seconds)

User says: "I need to launch a product in 3 weeks"

1. OrchestratorAgent loads session context from Vertex AI Memory Bank
2. PlannerAgent creates 4 milestones and 16 tasks, writes to AlloyDB
3. CalendarAgent books focus blocks in real Google Calendar
4. TaskAgent creates all tasks via custom MCP server
5. CommunicationAgent drafts and sends a Slack team update
6. MemoryAgent saves key decisions to Vertex AI Memory Bank
7. OrchestratorAgent returns: "Plan created with 4 milestones, 16 tasks, calendar blocked, team notified" — all in under 60 seconds

### Workflow 2 — Proactive Intelligence (No user input needed)

1. WatchAgent polls the database every 5 minutes
2. Detects a critical task due in 48 hours with a calendar conflict
3. Automatically proposes 3 alternative meeting times
4. Drafts a Slack message to the meeting organizer
5. Notifies the user: "I detected a conflict — reply to approve option 1"
6. User confirms in chat — ARIA handles the rest

### Workflow 3 — Cross-Session Memory

User asks in a new session: "What did we decide about pricing last week?"

1. MemoryAgent queries Vertex AI Memory Bank
2. Returns: "$49/month for individuals, $199/month for teams — premium justified by analytics features"
3. Accurate. Specific. Personalized. No re-explaining needed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Primary Agent | Gemini 2.5 Pro via Google ADK |
| Sub-Agents | Gemini 2.5 Flash via Google ADK |
| Framework | FastAPI + Python 3.11 |
| Database | AlloyDB (PostgreSQL) + pgvector |
| Memory | Vertex AI Memory Bank + AlloyDB |
| Calendar | Google Calendar API (OAuth 2.0) |
| Messaging | Slack SDK (real messages) |
| MCP Server | Custom FastMCP Task Server |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Google Cloud Run |
| Container | Docker |

---

## Project Structure

```
ARIA/
├── aria-backend/
│   ├── main.py                    # FastAPI app + all routes
│   ├── config.py                  # Settings from env vars
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── agents/
│   │   ├── orchestrator.py        # Primary OrchestratorAgent
│   │   ├── planner.py             # PlannerAgent
│   │   ├── calendar.py            # CalendarAgent (real Google Calendar)
│   │   ├── task.py                # TaskAgent
│   │   ├── memory.py              # MemoryAgent (Vertex AI + AlloyDB)
│   │   ├── vertex_memory.py       # Vertex AI Memory Bank integration
│   │   ├── communication.py       # CommunicationAgent (real Slack)
│   │   └── watch.py               # WatchAgent (proactive monitoring)
│   ├── mcp_servers/
│   │   └── task_server.py         # Custom FastMCP Task Server
│   └── db/
│       ├── client.py              # AlloyDB connection pool
│       ├── queries.py             # All DB query functions
│       └── schema.sql             # Database schema
└── aria-frontend/
    ├── src/
    │   └── App.jsx                # React chat interface
    ├── index.html
    └── package.json
```

---

## Database Schema

AlloyDB has 6 tables:

- users — profile, timezone, preferences, work style
- plans — goal text, milestones JSON array, deadline, status
- tasks — title, priority, due_date, status, plan_id, milestone
- events — calendar mirror with conflict detection flags
- memories — content, session_id, memory_type, importance
- watch_triggers — trigger rules, conditions JSON, last_fired

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| / | GET | Health check and system info |
| /health | GET | Service health status |
| /chat | POST | Main chat endpoint — routes to OrchestratorAgent |
| /status/{user_id} | GET | Current plans, tasks, memory count |
| /watch/trigger | GET | Manually trigger WatchAgent |

### Chat Request Example

```json
POST /chat
{
  "message": "I need to launch a product in 3 weeks",
  "user_id": "user-aadarsh-001",
  "session_id": "demo-session"
}
```

### Chat Response Example

```json
{
  "response": "I have created a 3-week launch plan with 4 milestones and 16 tasks. Your calendar has been updated and your team has been notified on Slack.",
  "agent_actions": [
    {"agent": "PlannerAgent", "status": "success", "summary": "Created plan with 4 milestones and 16 tasks"},
    {"agent": "TaskAgent", "status": "success", "summary": "Retrieved 16 tasks from database"},
    {"agent": "CalendarAgent", "status": "success", "summary": "Suggested schedule for 16 tasks"},
    {"agent": "CommunicationAgent", "status": "success", "summary": "Drafted Slack message for team"}
  ],
  "session_id": "demo-session",
  "user_id": "user-aadarsh-001"
}
```

---

## Setup and Run Locally

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- PostgreSQL running locally
- Google Cloud project with Vertex AI API enabled
- Slack Bot Token from api.slack.com
- Google OAuth 2.0 credentials with Calendar and Gmail scopes

### Backend Setup

```bash
git clone https://github.com/Aadarsh-Praveen/ARIA.git
cd ARIA
python -m venv venv
source venv/bin/activate
cd aria-backend
pip install -r requirements.txt
```

Create a .env file in the root ARIA folder with the variables listed below, then run:

```bash
python main.py
```

The backend starts on http://localhost:8000

### Frontend Setup

```bash
cd aria-frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

---

## Environment Variables

```
GOOGLE_CLOUD_PROJECT=aria-hackathon
GEMINI_API_KEY=your_gemini_api_key
ALLOYDB_DATABASE=aria
ALLOYDB_USER=your_db_user
ALLOYDB_PASSWORD=your_db_password
ALLOYDB_INSTANCE=project:region:instance
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_DEFAULT_CHANNEL=your_channel_id
VERTEX_AI_LOCATION=us-central1
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

---

## Judging Criteria Coverage

| Criteria | Weight | How ARIA Scores |
|---|---|---|
| Technical Implementation | 50% | 6 ADK agents with intelligent routing, real Google Calendar and Slack integrations, Vertex AI Memory Bank with cross-session recall, AlloyDB with 6 tables, custom FastMCP Task Server, deployed on Cloud Run |
| Innovation and Creativity | 30% | Proactive WatchAgent fires without user input (rare in hackathon submissions), persistent cross-session memory recalls exact decisions and numbers, semantic search with Gemini embeddings, all integrations are real not simulated |
| Demo and Documentation | 20% | 3-minute scripted demo video showing 3 distinct workflows, live Cloud Run URL, clean GitHub README with full API documentation, polished React UI that non-technical judges can understand immediately |

---

## Key Technical Decisions

**Why Vertex AI Memory Bank over a simple database?**
Vertex AI Memory Bank provides semantic recall — ARIA remembers not just what was stored but finds the most relevant memory for any query. Combined with AlloyDB as a fallback, the system is both powerful and resilient.

**Why a custom MCP server?**
The custom FastMCP Task Server gives ARIA full control over task creation, updates, and queries with a schema designed for multi-agent workflows — something generic MCP servers cannot provide.

**Why proactive WatchAgent?**
Most AI assistants are purely reactive. WatchAgent polls every 5 minutes and fires workflows autonomously — detecting deadline conflicts, overdue tasks, and calendar clashes before the user notices them.

---

## Built By

Aadarsh Praveen — Google Gen AI Academy APAC Hackathon 2026

ARIA is not a smarter chatbot. It is the missing coordination layer between you and your tools — one that works while you sleep.