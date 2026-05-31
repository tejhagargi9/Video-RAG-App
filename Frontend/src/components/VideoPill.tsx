export default function VideoPill({ id }: { id: string }) {
  const isA = id === "A";
  return (
    <span
      style={{
        background: isA ? "#1e1b4b" : "#2d1b3d",
        color: isA ? "#a5b4fc" : "#f0abfc",
        border: `1px solid ${isA ? "#3730a3" : "#7e22ce"}`,
        fontSize: 10,
        fontWeight: 700,
        padding: "2px 8px",
        borderRadius: 6,
        letterSpacing: "0.05em",
      }}
    >
      {id}
    </span>
  );
}