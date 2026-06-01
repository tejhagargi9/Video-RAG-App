import Icon from './Icon';

export default function UserMessage({ text }: { text: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end" }}>
      <div
        style={{
          maxWidth: "78%",
          background: "#4f46e5",
          color: "#fff",
          fontSize: 13.5,
          lineHeight: 1.65,
          padding: "10px 16px",
          borderRadius: "18px 18px 4px 18px",
        }}
      >
        {text}
      </div>
    </div>
  );
}

interface CitationChipProps {
  citation: {
    video: string;
    label: string;
    type: string;
  };
}

export function CitationChip({ citation }: CitationChipProps) {
  const isA = citation.video === "A";
  const iconName =
    citation.type === "clock" ? "clock" : citation.type === "chart" ? "chart-bar" : "quote";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: 11,
        padding: "3px 10px",
        borderRadius: 8,
        border: `1px solid ${isA ? "#3730a3" : "#6b21a8"}`,
        background: isA ? "#1e1b4b" : "#2d1b3d",
        color: isA ? "#a5b4fc" : "#e879f9",
        cursor: "pointer",
        whiteSpace: "nowrap",
      }}
    >
      <Icon name={iconName} style={{ fontSize: 11 }} />
      {citation.label}
    </span>
  );
}

interface AIMessageProps {
  msg: {
    id: number;
    route?: string;
    text?: string;
    citations?: Array<{ video: string; label: string; type: string }>;
    streaming?: boolean;
  };
}

export function AIMessage({ msg }: AIMessageProps) {
  const badge = routeBadgeStyle(msg.route || "unknown");
  const isStreaming = msg.streaming === true;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 6,
            background: badge.bg,
            color: badge.color,
            border: `1px solid ${badge.border}`,
          }}
        >
          {msg.route || "unknown"}
        </span>
        <span style={{ fontSize: 10, color: "#52525b" }}>Gemini 2.5 Flash</span>
      </div>

      <div
        style={{
          maxWidth: "88%",
          background: "#18181b",
          border: "1px solid #27272a",
          color: "#d4d4d8",
          fontSize: 13.5,
          lineHeight: 1.7,
          padding: "12px 16px",
          borderRadius: "4px 18px 18px 18px",
          whiteSpace: "pre-line",
        }}
      >
        {msg.text || ""}
        {isStreaming && (
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: 14,
              background: "#818cf8",
              borderRadius: 2,
              marginLeft: 3,
              verticalAlign: "middle",
              animation: "blink 0.9s steps(1) infinite",
            }}
          />
        )}
      </div>

      {!isStreaming && msg.citations && msg.citations.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, maxWidth: "88%" }}>
          {msg.citations.map((c, i) => (
            <CitationChip key={i} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div
      style={{
        display: "flex",
        gap: 5,
        padding: "10px 16px",
        background: "#18181b",
        border: "1px solid #27272a",
        borderRadius: "4px 18px 18px 18px",
        width: "fit-content",
        alignItems: "center",
      }}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#52525b",
            display: "inline-block",
            animation: `bounce 1.2s ease infinite`,
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
    </div>
  );
}

function routeBadgeStyle(route: string) {
  if (route.startsWith("stats")) return { bg: "#1e1f3a", color: "#818cf8", border: "#312e81" };
  if (route.startsWith("hook")) return { bg: "#2a1f0e", color: "#fbbf24", border: "#78350f" };
  if (route === "rag-response") return { bg: "#1e1f3a", color: "#818cf8", border: "#312e81" };
  return { bg: "#0f2a1e", color: "#34d399", border: "#065f46" };
}