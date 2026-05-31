import VideoCard from './VideoCard';

type VideoData = {
  A: { id: string; platform: string; creator: string; date: string; duration: string; views: string; likes: string; comments: string; followers: string; engagement: string; hashtags: string[]; chunks: number; };
  B: { id: string; platform: string; creator: string; date: string; duration: string; views: string; likes: string; comments: string; followers: string; engagement: string; hashtags: string[]; chunks: number; };
};

export default function Sidebar({ VIDEOS }: { VIDEOS: VideoData }) {
  return (
    <aside style={{ width: 320, flexShrink: 0, borderRight: "1px solid #1f1f23", display: "flex", flexDirection: "column", overflowY: "auto", background: "#09090b" }}>
      <div style={{ padding: "12px 16px 8px", fontSize: 9, color: "#3f3f46", textTransform: "uppercase", letterSpacing: "0.12em", fontWeight: 600 }}>Videos</div>
      {Object.values(VIDEOS).map((video) => (
        <VideoCard key={video.id} video={video} />
      ))}
      <ChunkBadges VIDEOS={VIDEOS} />
    </aside>
  );
}

function ChunkBadges({ VIDEOS }: { VIDEOS: VideoData }) {
  return (
    <div style={{ padding: "14px 16px" }}>
      <div
        style={{
          fontSize: 9,
          color: "#3f3f46",
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          fontWeight: 600,
          marginBottom: 10,
        }}
      >
        Chunks indexed · Pinecone
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {["A", "B"].map((id) => {
          const v = VIDEOS[id as keyof typeof VIDEOS];
          const isA = id === "A";
          return (
            <div
              key={id}
              style={{
                background: "#18181b",
                border: `1px solid ${isA ? "#312e81" : "#4a1d96"}`,
                borderRadius: 10,
                padding: "10px 12px",
              }}
            >
              <div style={{ fontSize: 9, color: "#52525b", marginBottom: 2 }}>Video {id}</div>
              <div
                style={{ fontSize: 24, fontWeight: 700, color: isA ? "#818cf8" : "#c084fc", lineHeight: 1 }}
              >
                {v.chunks}
              </div>
              <div style={{ fontSize: 9, color: "#3f3f46", marginTop: 3 }}>chunks · index</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}