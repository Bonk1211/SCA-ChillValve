import Hero from "./Hero";
import StackCard from "./StackCard";
import ClaimCard from "./ClaimCard";
import HowToRead from "./HowToRead";

export default function Landing({ onEnter }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "radial-gradient(circle at 50% -10%, #1a2640 0%, #0a1224 60%)",
        color: "#fff",
        fontFamily: "Inter, system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        gap: 28,
      }}
    >
      <Hero />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          width: "100%",
          maxWidth: 880,
        }}
      >
        <StackCard />
        <ClaimCard />
      </div>

      <button
        onClick={onEnter}
        className="mono"
        style={{
          background: "#22d3ee",
          color: "#0a1224",
          border: "none",
          padding: "14px 40px",
          borderRadius: 6,
          fontSize: 15,
          fontWeight: 700,
          letterSpacing: "0.16em",
          cursor: "pointer",
          boxShadow: "0 0 40px rgba(34, 211, 238, 0.35)",
          transition: "transform 0.12s ease, box-shadow 0.12s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = "translateY(-1px)";
          e.currentTarget.style.boxShadow = "0 0 60px rgba(34, 211, 238, 0.55)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "translateY(0)";
          e.currentTarget.style.boxShadow = "0 0 40px rgba(34, 211, 238, 0.35)";
        }}
      >
        ▶  OPEN THE SIMULATOR
      </button>

      <HowToRead />
    </div>
  );
}
