import { useState, useRef, useEffect } from "react"
import axios from "axios"

const API = "https://aria-backend-629352210643.us-central1.run.app"

const AGENT_LABELS = {
  PlannerAgent: "Built your project plan",
  TaskAgent: "Organized your tasks",
  MemoryAgent: "Saved to memory",
  CommunicationAgent: "Sent to Slack!",
  WatchAgent: "Checked for urgent issues",
  OrchestratorAgent: "Understood your goal",
  CalendarAgent: "Scheduled your calendar",
}

const SUGGESTIONS = [
  "Plan my product launch",
  "What are my priorities today?",
  "What did we decide last week?",
  "Check for urgent issues",
]

function formatMessage(text) {
  if (!text) return ""
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, '<code style="background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace">$1</code>')
    .replace(/^(\d+\.\s)/gm, "<br/>$1")
    .replace(/^(\*\s)/gm, "<br/>• ")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>")
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #19202D, #2E3543)", border: "1px solid rgba(70,69,84,0.3)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <span style={{ color: "#c0c1ff", fontWeight: 900, fontSize: 18 }}>A</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", background: "rgba(21,28,41,0.5)", borderRadius: 100, border: "1px solid rgba(70,69,84,0.1)" }}>
        <span style={{ fontSize: 11, color: "rgba(199,196,215,0.6)", fontWeight: 500 }}>ARIA is working on it</span>
        {[0.1, 0.2, 0.3].map((delay, i) => (
          <div key={i} style={{ width: 4, height: 4, borderRadius: "50%", background: "#c0c1ff", animation: `bounce 1s infinite ${delay}s` }} />
        ))}
      </div>
    </div>
  )
}

function ActionBadge({ label, status }) {
  const isError = status === "error"
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px",
      background: isError ? "rgba(255,70,70,0.1)" : "rgba(0,165,114,0.1)",
      border: `1px solid ${isError ? "rgba(255,70,70,0.2)" : "rgba(0,165,114,0.2)"}`,
      borderRadius: 100
    }}>
      <span style={{ color: isError ? "#ff6b6b" : "#4edea3", fontSize: 13 }} className="material-symbols-outlined">
        {isError ? "error" : "check_circle"}
      </span>
      <span style={{ fontSize: 10, fontWeight: 700, color: isError ? "#ff9999" : "#6ffbbe", textTransform: "uppercase", letterSpacing: "0.1em" }}>
        {label}
      </span>
    </div>
  )
}

function UserMessage({ text, time }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, maxWidth: "80%", alignSelf: "flex-end" }}>
      <div style={{ background: "linear-gradient(135deg, #c0c1ff, #8083ff)", color: "#0d0096", padding: "12px 24px", borderRadius: "18px 18px 0 18px", fontSize: 14, lineHeight: 1.6, fontWeight: 500 }}>
        {text}
      </div>
      <span style={{ fontSize: 10, color: "rgba(199,196,215,0.4)", marginRight: 8 }}>{time}</span>
    </div>
  )
}

function AssistantMessage({ text, actions, time }) {
  const labels = actions?.map(a => ({
    label: AGENT_LABELS[a.agent] || a.summary,
    status: a.status
  })).filter(Boolean) || []

  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 16, maxWidth: "90%" }}>
      <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #19202D, #2E3543)", border: "1px solid rgba(70,69,84,0.3)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <span style={{ color: "#c0c1ff", fontWeight: 900, fontSize: 18 }}>A</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div
          style={{ background: "#19202D", padding: "16px 24px", borderRadius: "18px 18px 18px 0", border: "1px solid rgba(70,69,84,0.1)", fontSize: 14, lineHeight: 1.8, color: "rgba(220,226,245,0.9)" }}
          dangerouslySetInnerHTML={{ __html: formatMessage(text) }}
        />
        {labels.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {labels.map((item, i) => <ActionBadge key={i} label={item.label} status={item.status} />)}
          </div>
        )}
        <span style={{ fontSize: 10, color: "rgba(199,196,215,0.4)", marginLeft: 4 }}>{time}</span>
      </div>
    </div>
  )
}

function TimelineItem({ text, sub, done }) {
  return (
    <div style={{ position: "relative", paddingLeft: 24 }}>
      <div style={{
        position: "absolute", left: -17, top: 2, width: 14, height: 14, borderRadius: "50%",
        background: done ? "#4edea3" : "#19202D",
        border: `2px solid ${done ? "#4edea3" : "rgba(70,69,84,0.4)"}`,
        display: "flex", alignItems: "center", justifyContent: "center"
      }}>
        {done && <span style={{ color: "#003824", fontSize: 9, fontWeight: 900 }} className="material-symbols-outlined">check</span>}
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: "#dce2f5" }}>{text}</span>
        <span style={{ fontSize: 10, color: "rgba(199,196,215,0.5)" }}>{sub}</span>
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([{
    role: "assistant",
    text: "Hello! I'm ARIA, your AI chief of staff. I coordinate multiple specialized agents to manage your tasks, schedule, and information — all working together so you don't have to. What do you need to accomplish today?",
    actions: [],
    time: now()
  }])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [watchLoading, setWatchLoading] = useState(false)
  const bottomRef = useRef(null)

  function now() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  useEffect(() => {
    fetchStatus()
    const i = setInterval(fetchStatus, 10000)
    return () => clearInterval(i)
  }, [])

  async function fetchStatus() {
    try {
      const r = await axios.get(`${API}/status/user-aadarsh-001`)
      setStatus(r.data)
    } catch {}
  }

  async function sendMessage(text) {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput("")
    setMessages(prev => [...prev, { role: "user", text: msg, actions: [], time: now() }])
    setLoading(true)
    setTimeline([{ text: "Understood your goal", sub: msg.slice(0, 35) + "...", done: true }])

    try {
      const res = await axios.post(`${API}/chat`, {
        message: msg,
        user_id: "user-aadarsh-001",
        session_id: "demo-session"
      })

      const actions = res.data.agent_actions || []
      const newTimeline = [
        { text: "Understood your goal", sub: msg.slice(0, 35) + "...", done: true },
        ...actions.map(a => ({
          text: AGENT_LABELS[a.agent] || a.agent,
          sub: a.status === "success" ? "Completed ✓" : a.status === "triggered" ? "Triggered !" : "Error",
          done: a.status === "success" || a.status === "triggered"
        }))
      ]
      setTimeline(newTimeline)

      setMessages(prev => [...prev, {
        role: "assistant",
        text: res.data.response,
        actions,
        time: now()
      }])
      fetchStatus()
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "Something went wrong connecting to ARIA. Please try again.",
        actions: [],
        time: now()
      }])
    }
    setLoading(false)
  }

  async function runProactiveCheck() {
    setWatchLoading(true)
    try {
      const res = await axios.get(`${API}/watch/trigger`)
      const msg = res.data.triggered > 0
        ? `⚠️ I found **${res.data.triggered} urgent item(s)** that need your attention!\n\n${res.data.results?.map(r => `• ${r.message}`).join("\n") || res.data.message}`
        : "✅ **All clear!** No urgent issues detected. Your schedule and tasks are on track."
      setMessages(prev => [...prev, {
        role: "assistant",
        text: msg,
        actions: [{ agent: "WatchAgent", status: res.data.triggered > 0 ? "triggered" : "success", summary: res.data.message }],
        time: now()
      }])
      setTimeline([
        { text: "Understood your goal", sub: "Proactive check...", done: true },
        { text: "Checked for urgent issues", sub: res.data.triggered > 0 ? `${res.data.triggered} trigger(s) fired` : "All clear", done: true }
      ])
    } catch {}
    setWatchLoading(false)
  }

  const completedTasks = status?.completed_tasks || 0
  const totalTasks = status?.total_tasks || 0
  const progressPct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0
  const circumference = 2 * Math.PI * 40
  const offset = circumference - (progressPct / 100) * circumference

  return (
    <div style={{ height: "100vh", display: "flex", overflow: "hidden", fontFamily: "'Inter', sans-serif", background: "#050B18", color: "#dce2f5" }}>

      {/* LEFT SIDEBAR */}
      <aside style={{ width: 240, height: "100%", background: "#151C29", display: "flex", flexDirection: "column", borderRight: "1px solid rgba(31,41,55,0.3)" }}>
        <div style={{ padding: "24px 24px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <h1 style={{ fontSize: 26, fontWeight: 900, letterSpacing: -1, background: "linear-gradient(135deg, #c0c1ff, #8083ff)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>ARIA</h1>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4edea3", animation: "pulseGreen 2s infinite" }} />
              <span style={{ fontSize: 10, color: "rgba(199,196,215,0.6)", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700 }}>Online</span>
            </div>
          </div>
          <p style={{ fontSize: 9, color: "rgba(199,196,215,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, lineHeight: 1.4 }}>Adaptive Role-based Intelligence Assistant</p>
        </div>

        <div style={{ flex: 1, padding: "0 16px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ height: 1, background: "rgba(70,69,84,0.15)" }} />

          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: "rgba(199,196,215,0.5)", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: 10, padding: "0 8px" }}>Try asking ARIA:</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => sendMessage(s)}
                  style={{ textAlign: "left", padding: "8px 14px", fontSize: 12, color: "rgba(199,196,215,0.7)", background: "#19202D", borderRadius: 100, border: "1px solid rgba(70,69,84,0.15)", cursor: "pointer", transition: "all 0.2s", lineHeight: 1.4 }}
                  onMouseEnter={e => { e.currentTarget.style.color = "#dce2f5"; e.currentTarget.style.borderColor = "rgba(192,193,255,0.3)" }}
                  onMouseLeave={e => { e.currentTarget.style.color = "rgba(199,196,215,0.7)"; e.currentTarget.style.borderColor = "rgba(70,69,84,0.15)" }}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div style={{ background: "#0D1321", padding: 16, borderRadius: 16, border: "1px solid rgba(70,69,84,0.15)" }}>
            <p style={{ fontSize: 10, fontWeight: 700, color: "rgba(199,196,215,0.5)", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: 14 }}>Today's Summary</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "Plans Active", value: status?.active_plans ?? "—", color: "#c0c1ff" },
                { label: "Tasks Pending", value: status?.pending_tasks ?? "—", color: "#ffb783" },
                { label: "Done Today", value: status?.completed_tasks ?? "—", color: "#4edea3" },
              ].map(item => (
                <div key={item.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "rgba(199,196,215,0.6)" }}>{item.label}</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: item.color }}>
                    {String(item.value ?? "0").padStart(2, "0")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ padding: 16 }}>
          <button onClick={runProactiveCheck} disabled={watchLoading}
            style={{ width: "100%", padding: "12px", background: "rgba(255,180,171,0.08)", border: "1px solid rgba(255,180,171,0.2)", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, color: "#ffb4ab", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", cursor: watchLoading ? "not-allowed" : "pointer" }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ffb4ab", animation: "pulseRed 2s infinite" }} />
            {watchLoading ? "Checking..." : "Run Proactive Check"}
          </button>
        </div>
      </aside>

      {/* MAIN CHAT */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", background: "#0D1321", overflow: "hidden" }}>
        <header style={{ height: 56, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 32px", borderBottom: "1px solid rgba(31,41,55,0.3)", background: "rgba(13,19,33,0.8)", backdropFilter: "blur(20px)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "#c0c1ff", fontSize: 18 }} className="material-symbols-outlined">auto_awesome</span>
            <span style={{ fontWeight: 700, fontSize: 14, color: "#dce2f5" }}>ARIA — Adaptive Role-based Intelligence Assistant</span>
          </div>
          <div style={{ fontSize: 10, color: "rgba(199,196,215,0.4)", fontWeight: 500, letterSpacing: "0.05em" }}>
            Powered by Gemini 2.5 · Google ADK · April 8, 2026
          </div>
        </header>

        <div style={{ flex: 1, overflowY: "auto", padding: "32px", display: "flex", flexDirection: "column", gap: 32, maxWidth: 800, margin: "0 auto", width: "100%" }}>
          <div style={{ display: "flex", justifyContent: "center" }}>
            <span style={{ fontSize: 10, color: "rgba(199,196,215,0.3)", background: "rgba(13,19,33,0.6)", padding: "4px 16px", borderRadius: 100, textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, border: "1px solid rgba(70,69,84,0.15)" }}>
              {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            </span>
          </div>

          {messages.map((msg, i) => (
            msg.role === "user"
              ? <UserMessage key={i} {...msg} />
              : <AssistantMessage key={i} {...msg} />
          ))}

          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        <div style={{ padding: "0 32px 32px" }}>
          <div style={{ maxWidth: 800, margin: "0 auto" }}>
            <div style={{ display: "flex", alignItems: "center", background: "rgba(46,53,67,0.5)", backdropFilter: "blur(20px)", borderRadius: 100, border: "1px solid rgba(70,69,84,0.2)", padding: "8px 8px 8px 24px" }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder="Ask ARIA anything..."
                style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 14, color: "#dce2f5", padding: "8px 0" }}
              />
              <button onClick={() => sendMessage()} disabled={loading || !input.trim()}
                style={{ width: 44, height: 44, borderRadius: "50%", background: !loading && input.trim() ? "linear-gradient(135deg, #c0c1ff, #8083ff)" : "rgba(70,69,84,0.3)", border: "none", cursor: !loading && input.trim() ? "pointer" : "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <span style={{ color: !loading && input.trim() ? "#07006c" : "rgba(199,196,215,0.3)", fontSize: 18 }} className="material-symbols-outlined">send</span>
              </button>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 10 }}>
              <span style={{ fontSize: 9, color: "rgba(199,196,215,0.3)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.1em" }} className="material-symbols-outlined">history</span>
              <span style={{ fontSize: 10, color: "rgba(199,196,215,0.3)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.1em" }}>ARIA remembers your context across sessions</span>
            </div>
          </div>
        </div>
      </main>

      {/* RIGHT PANEL */}
      <aside style={{ width: 280, height: "100%", background: "#151C29", borderLeft: "1px solid rgba(31,41,55,0.3)", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: 24, flex: 1, overflowY: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
            <h2 style={{ fontSize: 11, fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em", color: "rgba(199,196,215,0.5)" }}>What ARIA Did</h2>
            <span style={{ color: "#c0c1ff", fontSize: 16 }} className="material-symbols-outlined">bolt</span>
          </div>

          {timeline.length > 0 ? (
            <div style={{ position: "relative", paddingLeft: 24 }}>
              <div style={{ position: "absolute", left: 7, top: 8, bottom: 8, width: 1, background: "rgba(70,69,84,0.2)" }} />
              <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
                {timeline.map((item, i) => <TimelineItem key={i} {...item} />)}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "rgba(199,196,215,0.3)", lineHeight: 1.6, textAlign: "center", padding: "20px 0" }}>
              Send a message to see ARIA's actions here
            </div>
          )}
        </div>

        <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "#19202D", padding: 16, borderRadius: 16, border: "1px solid rgba(70,69,84,0.1)", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <p style={{ fontSize: 10, fontWeight: 700, color: "rgba(199,196,215,0.5)", textTransform: "uppercase", letterSpacing: "0.15em", alignSelf: "flex-start" }}>Your Progress</p>
            <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width={96} height={96} style={{ transform: "rotate(-90deg)" }}>
                <circle cx={48} cy={48} r={40} fill="transparent" stroke="rgba(70,69,84,0.3)" strokeWidth={8} />
                <circle cx={48} cy={48} r={40} fill="transparent" stroke="#c0c1ff" strokeWidth={8}
                  strokeDasharray={circumference} strokeDashoffset={offset}
                  strokeLinecap="round" style={{ transition: "stroke-dashoffset 0.5s ease" }} />
              </svg>
              <div style={{ position: "absolute", display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: "#dce2f5" }}>{progressPct}%</span>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { label: "Plans Created", value: status?.active_plans ?? 0, color: "#c0c1ff" },
              { label: "Tasks Done", value: status?.completed_tasks ?? 0, color: "#4edea3" },
              { label: "Total Tasks", value: status?.total_tasks ?? 0, color: "#ffb783" },
            ].map(item => (
              <div key={item.label} style={{ background: "#19202D", padding: "10px 14px", borderRadius: 12, border: "1px solid rgba(70,69,84,0.1)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: "rgba(199,196,215,0.5)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{item.label}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: item.color }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(70,69,84,0.4); border-radius: 2px; }
        input::placeholder { color: rgba(199,196,215,0.3); }
        @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
        @keyframes pulseGreen { 0% { box-shadow: 0 0 0 0 rgba(78,222,163,0.5); } 70% { box-shadow: 0 0 0 8px rgba(78,222,163,0); } 100% { box-shadow: 0 0 0 0 rgba(78,222,163,0); } }
        @keyframes pulseRed { 0% { box-shadow: 0 0 0 0 rgba(255,180,171,0.5); } 70% { box-shadow: 0 0 0 8px rgba(255,180,171,0); } 100% { box-shadow: 0 0 0 0 rgba(255,180,171,0); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        strong { color: #e8e8ff; font-weight: 700; }
        em { color: #c0c1ff; font-style: italic; }
      `}</style>
    </div>
  )
}