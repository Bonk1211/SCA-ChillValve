function BigButton({ onClick, color, outline, icon, children, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="mono"
      style={{
        background: outline ? "transparent" : color,
        color: outline ? color : "#0a1224",
        border: `1.5px solid ${color}`,
        borderRadius: 4,
        padding: "6px 14px",
        fontSize: 11,
        fontWeight: 700,
        cursor: disabled ? "not-allowed" : "pointer",
        letterSpacing: "0.1em",
        display: "flex",
        alignItems: "center",
        gap: 6,
        minWidth: 110,
        justifyContent: "center",
        opacity: disabled ? 0.35 : 1,
        transition: "opacity 0.15s",
      }}
    >
      {icon}
      {children}
    </button>
  );
}

export default function ControlBar({
  onReplay,
  onStart,
  onStop,
  busy,
  engineState,    // "idle" | "running" | "paused"
  canReplay,      // false if no scenario picked yet
}) {
  const isRunning = engineState === "running";
  const isPaused = engineState === "paused";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        padding: "4px 14px",
        background: "#0f1a30",
        borderTop: "1px solid #2d3d5e",
      }}
    >
      <BigButton
        onClick={onStart}
        disabled={busy || isRunning}
        color="#34d399"
        icon={
          <svg width="14" height="14" viewBox="0 0 14 14">
            <polygon points="3,2 12,7 3,12" fill="#0a1224" />
          </svg>
        }
      >
        {busy ? "WORKING…" : isPaused ? "RESUME" : "START"}
      </BigButton>
      <BigButton
        onClick={onStop}
        disabled={busy || !isRunning}
        color="#f87171"
        outline
        icon={
          <svg width="14" height="14" viewBox="0 0 14 14">
            <rect x="3" y="3" width="8" height="8" fill="#f87171" />
          </svg>
        }
      >
        STOP
      </BigButton>
      <span style={{ width: 1, height: 22, background: "#2d3d5e", margin: "0 4px" }} />
      <BigButton
        onClick={onReplay}
        color="#fbbf24"
        outline
        disabled={busy || !canReplay}
        icon={
          <svg width="14" height="14" viewBox="0 0 14 14">
            <path
              d="M 11 7 a 4 4 0 1 1 -4 -4 M 6 1 L 7 3 L 6 4"
              fill="none"
              stroke="#fbbf24"
              strokeWidth="1.5"
            />
          </svg>
        }
      >
        REPLAY
      </BigButton>
    </div>
  );
}
