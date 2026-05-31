import { useState, useRef, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from './Sidebar';
import UserMessage from './Message';
import { AIMessage, TypingIndicator } from './Message';
import Icon from './Icon';

const DEFAULT_VIDEOS = {
  A: {
    id: "A",
    platform: "youtube",
    creator: "@mkbhd",
    date: "Apr 12 2024",
    duration: "0:58",
    views: "2.4M",
    likes: "142K",
    comments: "3.8K",
    followers: "18.2M",
    engagement: "6.08",
    hashtags: ["#shorts", "#tech", "#review"],
    chunks: 7,
  },
  B: {
    id: "B",
    platform: "instagram",
    creator: "@techwithtim",
    date: "Apr 9 2024",
    duration: "1:02",
    views: "890K",
    likes: "41K",
    comments: "920",
    followers: "4.1M",
    engagement: "4.71",
    hashtags: ["#python", "#coding", "#reels"],
    chunks: 5,
  },
};

type VideoData = typeof DEFAULT_VIDEOS;

const SAMPLE_RESPONSES = [
  {
    route: "comparison",
    text: "Video A outperformed B mainly because of its hook strength — within 3 seconds it uses a direct question that creates immediate curiosity. Video B opens with a static title card which loses ~40% of viewers before the content starts.\n\nOn engagement, A achieves 6.08% vs B's 4.71% — meaningful given A has 4× more followers, suggesting the content resonated far beyond its existing audience.",
    citations: [
      { video: "A", label: "A · 0:00–0:05 · chunk 1", type: "quote" },
      { video: "B", label: "B · 0:00–0:04 · chunk 1", type: "quote" },
      { video: "A", label: "A stats", type: "chart" },
      { video: "B", label: "B stats", type: "chart" },
    ],
  },
  {
    route: "stats",
    text: "Video A: 6.08% engagement rate (142K likes + 3.8K comments / 2.4M views).\nVideo B: 4.71% engagement rate (41K likes + 920 comments / 890K views).\n\nA leads by ~1.4 percentage points despite having a much larger audience to satisfy.",
    citations: [
      { video: "A", label: "A stats", type: "chart" },
      { video: "B", label: "B stats", type: "chart" },
    ],
  },
  {
    route: "hook · <5s",
    text: 'Video A hook: Opens mid-action with a provocative question — "Is this actually better?" — while showing the product in-hand. Immediate pattern interrupt.\n\nVideo B hook: Text overlay on a static background reads the title aloud. Functional but low-energy — no visual movement to retain scroll-stopping attention.',
    citations: [
      { video: "A", label: "A · 0:00–0:05", type: "clock" },
      { video: "B", label: "B · 0:00–0:04", type: "clock" },
    ],
  },
  {
    route: "comparison",
    text: "Suggested improvements for B based on A:\n1) Replace the static title hook with a mid-action open.\n2) Add a direct question in the first 3 seconds to trigger curiosity.\n3) Shorten the intro by ~8 seconds — A reaches value faster.\n4) Add a pattern-interrupt visual (zoom or cut) at the 5-second mark.",
    citations: [
      { video: "A", label: "A · chunk 1–2", type: "quote" },
      { video: "B", label: "B · chunk 1", type: "quote" },
    ],
  },
];

const SUGGESTIONS = [
  "Why did A outperform B?",
  "Compare the hooks",
  "Engagement rates",
  "Creator of B + followers",
  "Improve B based on A",
];

function getStoredVideoData(): VideoData {
  const stored = localStorage.getItem('videorag_ingest_data');
  if (stored) {
    try {
      const data = JSON.parse(stored);
      const updated = { ...DEFAULT_VIDEOS };
      if (data.video_a) {
        const meta = data.video_a.metadata || {};
        updated.A = {
          ...updated.A,
          ...meta,
          views: data.video_a.views || DEFAULT_VIDEOS.A.views,
          likes: data.video_a.likes || DEFAULT_VIDEOS.A.likes,
          engagement: data.video_a.engagement_rate || DEFAULT_VIDEOS.A.engagement,
          chunks: data.video_a.chunks || DEFAULT_VIDEOS.A.chunks,
          creator: meta.channel_title || meta.creator || DEFAULT_VIDEOS.A.creator,
          hashtags: meta.hashtags || DEFAULT_VIDEOS.A.hashtags,
        };
      }
      if (data.video_b) {
        const meta = data.video_b.metadata || {};
        updated.B = {
          ...updated.B,
          ...meta,
          views: data.video_b.views || DEFAULT_VIDEOS.B.views,
          likes: data.video_b.likes || DEFAULT_VIDEOS.B.likes,
          engagement: data.video_b.engagement_rate || DEFAULT_VIDEOS.B.engagement,
          chunks: data.video_b.chunks || DEFAULT_VIDEOS.B.chunks,
          creator: meta.username || meta.creator || DEFAULT_VIDEOS.B.creator,
          hashtags: meta.hashtags || DEFAULT_VIDEOS.B.hashtags,
        };
      }
      return updated;
    } catch (e) {
      console.error('Failed to parse ingest data', e);
    }
  }
  return DEFAULT_VIDEOS;
}

export default function VSChatPage() {
  const navigate = useNavigate();
  type Message = { id: number; role: string; text?: string; route?: string; citations?: Array<{ video: string; label: string; type: string }>; streaming: boolean };
  const [messages, setMessages] = useState<Array<Message>>([
    { id: 1, role: "user", text: "Why did Video A get more engagement than Video B?", streaming: false },
    {
      id: 2,
      role: "ai",
      route: SAMPLE_RESPONSES[0].route,
      text: SAMPLE_RESPONSES[0].text,
      citations: SAMPLE_RESPONSES[0].citations,
      streaming: false,
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [responseIdx, setResponseIdx] = useState(1);
  const videoData = useMemo(() => getStoredVideoData(), []);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const sendMessage = (text: string) => {
    if (!text.trim() || isTyping) return;
    setMessages((prev) => [...prev, { id: Date.now(), role: "user", text: text.trim()!, streaming: false }]);
    setInput("");
    setIsTyping(true);

    const response = SAMPLE_RESPONSES[responseIdx % SAMPLE_RESPONSES.length];
    setResponseIdx((i) => i + 1);

    setTimeout(() => {
      setIsTyping(false);
      const aiId = Date.now() + 1;
      const words = response.text.split(" ");
      let current = "";

      setMessages((prev) => [
        ...prev,
        { id: aiId, role: "ai", route: response.route, text: "", citations: [], streaming: true },
      ]);

      let i = 0;
      const iv = setInterval(() => {
        current += (i === 0 ? "" : " ") + words[i];
        i++;
        setMessages((prev) =>
          prev.map((m) => (m.id === aiId ? { ...m, text: current } : m))
        );
        if (i >= words.length) {
          clearInterval(iv);
          setTimeout(() => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId
                  ? { ...m, text: response.text, citations: response.citations, streaming: false }
                  : m
              )
            );
          }, 200);
        }
      }, 38);
    }, 1000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#09090b", color: "#d4d4d8", fontFamily: "system-ui, sans-serif", overflow: "hidden" }}>

      {/* Topbar */}
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px", height: 52, borderBottom: "1px solid #1f1f23", background: "#09090b", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: "linear-gradient(135deg,#6366f1,#a855f7)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 11, fontWeight: 800 }}>VS</div>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#f4f4f5" }}>VS.</span>
          <span style={{ fontSize: 13, color: "#52525b" }}>Video Comparison RAG</span>
        </div>
        <button
          onClick={() => navigate('/')}
          style={{ fontSize: 12, color: "#71717a", padding: "6px 14px", borderRadius: 8, background: "#18181b", border: "1px solid #27272a", cursor: "pointer" }}
          onMouseOver={e => e.currentTarget.style.color = "#d4d4d8"}
          onMouseOut={e => e.currentTarget.style.color = "#71717a"}
        >
          Re-ingest
        </button>
      </header>

      {/* Body */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Sidebar */}
        <Sidebar VIDEOS={videoData} />

        {/* Chat */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "#09090b" }}>

          {/* Chat header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px", height: 48, borderBottom: "1px solid #1f1f23", flexShrink: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e", boxShadow: "0 0 8px #22c55e", display: "inline-block" }} />
              <span style={{ fontSize: 13, fontWeight: 500, color: "#e4e4e7" }}>RAG Chat</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 10, color: "#3f3f46", fontFamily: "monospace" }}>thread_8f2a91c</span>
              <button
                onClick={() => setMessages([])}
                style={{ fontSize: 11, color: "#71717a", padding: "4px 10px", borderRadius: 6, background: "transparent", border: "1px solid #27272a", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                onMouseOver={e => { e.currentTarget.style.color = "#f87171"; e.currentTarget.style.borderColor = "#7f1d1d"; }}
                onMouseOut={e => { e.currentTarget.style.color = "#71717a"; e.currentTarget.style.borderColor = "#27272a"; }}
              >
                <Icon name="trash" style={{ fontSize: 11 }} /> Clear
              </button>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: 18 }}>
            {messages.length === 0 && (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ color: "#3f3f46", fontSize: 13 }}>Ask a comparison question to get started.</p>
              </div>
            )}
            {messages.map((msg) =>
              msg.role === "user"
                ? <UserMessage key={msg.id} text={msg.text || ""} />
                : <AIMessage key={msg.id} msg={msg} />
            )}
            {isTyping && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 20px 12px" }}>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                disabled={isTyping}
                style={{ fontSize: 11.5, color: "#71717a", padding: "5px 12px", borderRadius: 20, background: "#18181b", border: "1px solid #27272a", cursor: "pointer", opacity: isTyping ? 0.4 : 1 }}
                onMouseOver={e => { if (!isTyping) { e.currentTarget.style.color = "#a5b4fc"; e.currentTarget.style.borderColor = "#3730a3"; e.currentTarget.style.background = "#1e1b4b"; } }}
                onMouseOut={e => { e.currentTarget.style.color = "#71717a"; e.currentTarget.style.borderColor = "#27272a"; e.currentTarget.style.background = "#18181b"; }}
              >
                {s} ↗
              </button>
            ))}
          </div>

          {/* Input */}
          <div style={{ padding: "0 16px 16px", flexShrink: 0 }}>
            <div
              style={{ display: "flex", alignItems: "flex-end", gap: 10, background: "#18181b", border: "1px solid #27272a", borderRadius: 14, padding: "10px 14px" }}
              onFocusCapture={e => e.currentTarget.style.borderColor = "#4338ca"}
              onBlurCapture={e => e.currentTarget.style.borderColor = "#27272a"}
            >
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
                placeholder="Ask a comparison question…"
                disabled={isTyping}
                style={{ flex: 1, background: "transparent", color: "#e4e4e7", fontSize: 13.5, lineHeight: 1.6, resize: "none", outline: "none", border: "none", maxHeight: 120, opacity: isTyping ? 0.5 : 1 }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isTyping}
                style={{ width: 34, height: 34, borderRadius: 10, background: input.trim() && !isTyping ? "#4f46e5" : "#27272a", border: "none", cursor: input.trim() && !isTyping ? "pointer" : "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "background 0.15s" }}
              >
                <Icon name="send" style={{ fontSize: 15, color: input.trim() && !isTyping ? "#fff" : "#52525b" }} />
              </button>
            </div>
            <p style={{ fontSize: 10, color: "#27272a", textAlign: "center", marginTop: 6, letterSpacing: "0.05em" }}>
              LangGraph · Pinecone · OpenAI
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}