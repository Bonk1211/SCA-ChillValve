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

export default function ControlBar({ stepIdx, totalSteps, onPrev, onNext, onReplay, busy }) {
  const atStart = stepIdx === 0;
  const atEnd = stepIdx === totalSteps - 1;
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
        onClick={onPrev}
        disabled={atStart || busy}
        color="#9aacc8"
        outline
        icon={
          <svg width="14" height="14" viewBox="0 0 14 14">
            <polygon points="11,2 2,7 11,12" fill="#9aacc8" />
          </svg>
        }
      >
        PREV
      </BigButton>
      <BigButton
        onClick={onNext}
        disabled={atEnd || busy}
        color="#22d3ee"
        icon={
          <svg width="14" height="14" viewBox="0 0 14 14">
            <polygon points="3,2 12,7 3,12" fill="#0a1224" />
          </svg>
        }
      >
        {busy ? "WORKING…" : "NEXT STEP ›"}
      </BigButton>
      <BigButton
        onClick={onReplay}
        color="#fbbf24"
        outline
        disabled={busy}
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
