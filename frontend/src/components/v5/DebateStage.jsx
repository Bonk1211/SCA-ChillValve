import { useEffect, useRef, useState } from "react";
import { useDashboardStore } from "../../store/useDashboardStore";
import { VALVES } from "../../lib/valveConfig";

const CHAR_DELAY_MS = 22;
const PHASE_PAUSE_MS = 450;
const BRANCHES = ["A", "B"];

function ValveBubble({ vid, text, isLeader, isActive, isDone, isCached, allocPct }) {
  const accent = isLeader ? "#22d3ee" : "#a78bfa";
  const showText = isActive || isDone || isCached;
  return (
    <div
      style={{
        position: "relative",
        flex: isLeader ? 1.4 : 1,
        minWidth: 0,
        background: isActive ? `${accent}1c` : "#131f37",
        border: `1.5px solid ${isActive ? accent : `${accent}55`}`,
        borderRadius: 5,
        padding: "5px 7px",
        display: "flex",
        flexDirection: "column",
        gap: 3,
        boxShadow: isActive ? `0 0 14px ${accent}55, inset 0 0 12px ${accent}22` : "none",
        transition: "background 0.2s, border 0.2s, box-shadow 0.2s",
        opacity: isActive || isDone || isCached ? 1 : 0.5,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
        <span
          className="mono"
          style={{ fontSize: 13, fontWeight: 700, color: "#fff", letterSpacing: "0.04em" }}
        >
          {vid}
        </span>
        {isLeader ? (
          <span
            className="mono"
            style={{
              fontSize: 8,
              fontWeight: 700,
              color: "#0a1224",
              background: accent,
              padding: "1px 3px",
              borderRadius: 2,
              letterSpacing: "0.1em",
            }}
          >
            LEADER
          </span>
        ) : (
          <span
            className="mono"
            style={{ fontSize: 8, fontWeight: 600, color: accent, letterSpacing: "0.1em" }}
          >
            PEER
          </span>
        )}
        {isActive && (
          <span style={{ display: "flex", alignItems: "center", gap: 3, marginLeft: "auto" }}>
            <span
              style={{
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: accent,
                animation: "debatePulse 0.9s ease-in-out infinite",
              }}
            />
            <span
              className="mono"
              style={{ fontSize: 8, color: accent, fontWeight: 600, letterSpacing: "0.1em" }}
            >
              {isLeader ? "SYNTH" : "SPEAK"}
            </span>
          </span>
        )}
        {allocPct != null && (isDone || isCached) && (
          <span
            className="mono"
            style={{
              marginLeft: "auto",
              fontSize: 11,
              fontWeight: 700,
              color: accent,
              padding: "1px 5px",
              background: `${accent}1c`,
              borderRadius: 2,
            }}
          >
            → {allocPct.toFixed(0)}%
          </span>
        )}
      </div>
      <div
        className="mono"
        style={{
          fontSize: 11,
          color: showText ? "#d1dcec" : "#445574",
          lineHeight: 1.4,
          minHeight: 70,
          fontStyle: isLeader ? "normal" : "italic",
        }}
      >
        {showText ? text || "…" : "(waiting)"}
        {isActive && (
          <span
            style={{
              display: "inline-block",
              width: 6,
              height: 11,
              background: accent,
              marginLeft: 2,
              verticalAlign: "text-bottom",
              animation: "debateCaret 0.6s steps(1) infinite",
            }}
          />
        )}
      </div>
    </div>
  );
}

function BranchPanel({ branchId, debate, animState }) {
  if (!debate) {
    return (
      <div
        style={{
          background: "#0f1a30",
          border: "1px solid #2d3d5e",
          borderRadius: 5,
          padding: 6,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 4,
            flexShrink: 0,
          }}
        >
          <span
            className="mono"
            style={{
              fontSize: 8,
              color: "#0a1224",
              background: "#a78bfa",
              padding: "1px 5px",
              borderRadius: 2,
              fontWeight: 700,
              letterSpacing: "0.1em",
            }}
          >
            L3
          </span>
          <span
            className="mono"
            style={{ fontSize: 10, color: "#a78bfa", fontWeight: 700, letterSpacing: "0.1em" }}
          >
            BRANCH {branchId}
          </span>
          <span
            className="mono"
            style={{ fontSize: 9, color: "#9aacc8", marginLeft: "auto", fontStyle: "italic" }}
          >
            idle
          </span>
        </div>
        <div
          className="mono"
          style={{
            fontSize: 10,
            color: "#9aacc8",
            fontStyle: "italic",
            padding: "8px 6px",
            textAlign: "center",
          }}
        >
          no debate fired yet on branch {branchId}
        </div>
      </div>
    );
  }

  const speechByValve = Object.fromEntries(
    debate.speeches.map((s) => [s.valve_id, s.text]),
  );
  const branchValves = VALVES.filter((v) => v.branch === debate.branch_id).map(
    (v) => v.id,
  );
  const peerIds = branchValves.filter((vid) => vid !== debate.leader_id);
  const phases = [
    ...peerIds.map((vid) => ({
      vid,
      text: speechByValve[vid] ?? "(no speech recorded)",
      isLeader: false,
    })),
    { vid: debate.leader_id, text: debate.rationale, isLeader: true },
  ];

  const { activeIdx = -1, displayed = {} } = animState ?? {};

  return (
    <div
      style={{
        background: "#0f1a30",
        border: "1px solid #2d3d5e",
        borderRadius: 5,
        padding: 6,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        gap: 5,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
        <span
          className="mono"
          style={{
            fontSize: 8,
            color: "#0a1224",
            background: "#a78bfa",
            padding: "1px 5px",
            borderRadius: 2,
            fontWeight: 700,
            letterSpacing: "0.1em",
          }}
        >
          L3
        </span>
        <span
          className="mono"
          style={{ fontSize: 10, color: "#a78bfa", fontWeight: 700, letterSpacing: "0.1em" }}
        >
          BRANCH {debate.branch_id}
        </span>
        <span className="mono" style={{ fontSize: 9, color: "#9aacc8", marginLeft: "auto" }}>
          t={debate.tick} · {(debate.wall_clock_s ?? 0).toFixed(2)}s
          {debate.cached && " · CACHED"}
          {activeIdx >= 0 && " · LIVE"}
        </span>
      </div>

      <div style={{ display: "flex", gap: 5, alignItems: "stretch" }}>
        {phases.map((phase, i) => (
          <ValveBubble
            key={phase.vid}
            vid={phase.vid}
            text={displayed[phase.vid] ?? ""}
            isLeader={phase.isLeader}
            isActive={activeIdx === i}
            isDone={activeIdx > i || activeIdx === -1}
            isCached={debate.cached}
            allocPct={phase.isLeader ? null : debate.allocations?.[phase.vid]}
          />
        ))}
      </div>

    </div>
  );
}

function RecoveryBar({ remediation }) {
  if (!remediation) return null;
  const branchOf = VALVES.find((v) => v.id === remediation.target_valve_id)?.branch;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "5px 10px",
        background: `${remediation.executed ? "#34d399" : "#fbbf24"}1c`,
        border: `1.5px solid ${remediation.executed ? "#34d399" : "#fbbf24"}`,
        borderRadius: 5,
        flexWrap: "wrap",
      }}
    >
      <span
        className="mono"
        style={{
          fontSize: 9,
          fontWeight: 700,
          color: "#0a1224",
          background: remediation.executed ? "#34d399" : "#fbbf24",
          padding: "2px 6px",
          borderRadius: 2,
          letterSpacing: "0.1em",
        }}
      >
        AUTONOMOUS RECOVERY
      </span>
      {branchOf && (
        <span
          className="mono"
          style={{
            fontSize: 9,
            fontWeight: 700,
            color: "#a78bfa",
            border: "1px solid #a78bfa",
            padding: "1px 5px",
            borderRadius: 2,
            letterSpacing: "0.1em",
          }}
        >
          BRANCH {branchOf}
        </span>
      )}
      <span
        className="mono"
        style={{ fontSize: 12, fontWeight: 700, color: "#fff", letterSpacing: "0.04em" }}
      >
        {remediation.target_valve_id} →{" "}
        {(remediation.action ?? "unknown").replaceAll("_", " ").toUpperCase()}
      </span>
      {remediation.executed && (
        <span
          className="mono"
          style={{ fontSize: 9, fontWeight: 700, color: "#34d399", letterSpacing: "0.1em" }}
        >
          ✓ EXECUTED · fault clearing
        </span>
      )}
      <span
        style={{
          fontSize: 11,
          color: "#d1dcec",
          fontStyle: "italic",
          flex: 1,
          minWidth: 120,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        "{remediation.rationale}"
      </span>
      <span className="mono" style={{ fontSize: 9, color: "#9aacc8" }}>
        tick {remediation.tick ?? "?"} · {(remediation.wall_clock_s ?? 0).toFixed(2)}s wall
      </span>
    </div>
  );
}

export default function DebateStage() {
  const debates = useDashboardStore((s) => s.debates);
  const latestRemediation = useDashboardStore((s) => s.latestRemediation);

  // Compute latest debate per branch.
  const latestByBranch = {};
  for (const d of debates) latestByBranch[d.branch_id] = d;

  // Per-branch animation state.
  const [animByBranch, setAnimByBranch] = useState({});
  const timersRef = useRef({});       // branchId → timeoutId
  const lastKeyRef = useRef({});      // branchId → animation key

  useEffect(() => {
    for (const branchId of BRANCHES) {
      const latest = latestByBranch[branchId];
      if (!latest) continue;
      const key = `${latest.tick}|${latest.cached ? "c" : "f"}`;
      if (lastKeyRef.current[branchId] === key) continue;
      lastKeyRef.current[branchId] = key;
      clearTimeout(timersRef.current[branchId]);

      if (latest.cached) {
        const all = {};
        for (const s of latest.speeches) all[s.valve_id] = s.text;
        all[latest.leader_id] = latest.rationale;
        setAnimByBranch((prev) => ({ ...prev, [branchId]: { activeIdx: -1, displayed: all } }));
        continue;
      }

      const speechByValve = Object.fromEntries(
        latest.speeches.map((s) => [s.valve_id, s.text]),
      );
      const branchValves = VALVES.filter((v) => v.branch === branchId).map((v) => v.id);
      const peerIds = branchValves.filter((vid) => vid !== latest.leader_id);
      const phases = [
        ...peerIds.map((vid) => ({
          vid,
          text: speechByValve[vid] ?? "(no speech recorded)",
        })),
        { vid: latest.leader_id, text: latest.rationale },
      ];

      let pIdx = 0;
      let cIdx = 0;
      const accum = {};
      setAnimByBranch((prev) => ({ ...prev, [branchId]: { activeIdx: 0, displayed: {} } }));

      const step = () => {
        if (pIdx >= phases.length) {
          setAnimByBranch((prev) => ({
            ...prev,
            [branchId]: { ...prev[branchId], activeIdx: -1 },
          }));
          return;
        }
        const phase = phases[pIdx];
        if (cIdx > phase.text.length) {
          timersRef.current[branchId] = setTimeout(() => {
            pIdx++;
            cIdx = 0;
            if (pIdx < phases.length) {
              setAnimByBranch((prev) => ({
                ...prev,
                [branchId]: { ...prev[branchId], activeIdx: pIdx },
              }));
            }
            step();
          }, PHASE_PAUSE_MS);
          return;
        }
        accum[phase.vid] = phase.text.slice(0, cIdx);
        setAnimByBranch((prev) => ({
          ...prev,
          [branchId]: { ...prev[branchId], displayed: { ...accum } },
        }));
        cIdx++;
        timersRef.current[branchId] = setTimeout(step, CHAR_DELAY_MS);
      };
      step();
    }
    return () => {
      for (const t of Object.values(timersRef.current)) clearTimeout(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debates]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minHeight: 0,
      }}
    >
      <RecoveryBar remediation={latestRemediation} />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 6,
          minHeight: 0,
        }}
      >
        {BRANCHES.map((branchId) => (
          <BranchPanel
            key={branchId}
            branchId={branchId}
            debate={latestByBranch[branchId] ?? null}
            animState={animByBranch[branchId]}
          />
        ))}
      </div>
      <style>{`
        @keyframes debatePulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.7); } }
        @keyframes debateCaret { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
      `}</style>
    </div>
  );
}
