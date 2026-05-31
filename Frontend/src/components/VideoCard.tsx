import { default as Icon } from './Icon';
import { default as VideoPill } from './VideoPill';

interface StatChipProps {
  icon: string;
  value: string | number;
}

function StatChip({ icon, value }: StatChipProps) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        padding: "3px 8px",
        borderRadius: 6,
        border: "1px solid #27272a",
        background: "#18181b",
        color: "#71717a",
      }}
    >
      <Icon name={icon} style={{ fontSize: 11 }} />
      {value}
    </span>
  );
}

interface VideoCardProps {
  video: {
    id: string;
    platform: string;
    creator: string;
    date: string;
    duration: string;
    views: string;
    likes: string;
    comments: string;
    followers: string;
    engagement: string;
    hashtags: string[];
  };
}

export default function VideoCard({ video }: VideoCardProps) {
  const isA = video.id === "A";
  const engHigh = parseFloat(video.engagement) > 5;

  return (
    <div
      style={{
        padding: "14px 16px",
        borderBottom: "1px solid #1f1f23",
      }}
    >
      {/* header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <VideoPill id={video.id} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: isA ? "#818cf8" : "#c084fc" }}>
            {video.creator}
          </div>
          <div style={{ fontSize: 10, color: "#52525b", marginTop: 1 }}>
            {video.platform === "youtube" ? "YouTube" : "Instagram"} · {video.duration} · {video.date}
          </div>
        </div>
        <Icon
          name={video.platform === "youtube" ? "brand-youtube" : "brand-instagram"}
          style={{ fontSize: 16, color: video.platform === "youtube" ? "#7f1d1d" : "#581c87" }}
        />
      </div>

      {/* thumb + stats */}
      <div style={{ display: "flex", gap: 12 }}>
        <div
          style={{
            width: 72,
            height: 52,
            borderRadius: 8,
            flexShrink: 0,
            background: "#18181b",
            border: "1px solid #27272a",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <Icon
            name={video.platform === "youtube" ? "brand-youtube" : "brand-instagram"}
            style={{ fontSize: 22, color: "#3f3f46" }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: "rgba(255,255,255,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Icon name="player-play" style={{ fontSize: 9, color: "#fff", marginLeft: 1 }} />
            </div>
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            <StatChip icon="eye" value={video.views} />
            <StatChip icon="heart" value={video.likes} />
            <StatChip icon="message-circle" value={video.comments} />
            <StatChip icon="users" value={video.followers} />
          </div>

          <span
            style={{
              alignSelf: "flex-start",
              fontSize: 11,
              fontWeight: 600,
              padding: "3px 8px",
              borderRadius: 6,
              background: engHigh ? "#052e16" : "#1a2e05",
              border: `1px solid ${engHigh ? "#14532d" : "#365314"}`,
              color: engHigh ? "#4ade80" : "#a3e635",
            }}
          >
            ↑ {video.engagement}% engagement
          </span>

          {/* <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {video.hashtags.map((h) => (
              <span
                key={h}
                style={{
                  fontSize: 10,
                  color: "#3f3f46",
                  background: "#18181b",
                  border: "1px solid #27272a",
                  borderRadius: 4,
                  padding: "1px 6px",
                }}
              >
                {h}
              </span>
            ))}
          </div> */}
        </div>
      </div>
    </div>
  );
}