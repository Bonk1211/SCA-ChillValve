import { useEffect, useRef, useState } from "react";
import { useDashboardStore } from "../../store/useDashboardStore";
import { VALVES } from "../../lib/valveConfig";

const CHAR_DELAY_MS = 65;           // slow typewriter so judges can read each word
const PHASE_PAUSE_MS = 1500;        // long hold between peer bubbles
const LEADER_SYNTH_PAUSE_MS = 1800; // leader stares at INPUTS before typing DECISION
const BRANCHES = ["A", "B"];

const REQUEST_LABEL = {
  open_more: "OPEN +",
  hold: "HOLD",
  take_load: "TAKE LOAD",
  close_more: "CLOSE −",
};
const REQUEST_COLOR = {
  open_more: "#34d399",
  hold: "#9aacc8",
  take_load: "#22d3ee",
  close_more: "#fbbf24",
};

function StatusChip({ status }) {
  if (!status) return null;
  const isImpaired = status === "impaired";
  const bg = isImpaired ? "#f87171" : "#34d399";
  return (
    <span
      className="mono"
      style={{
        fontSize: 11,
        fontWeight: 700,
        color: "#0a1224",
        background: bg,
        padding: "2px 6px",
        borderRadius: 3,
        letterSpacing: "0.1em",
      }}
    >
      {isImpaired ? "IMPAIRED" : "NOMINAL"}
    </span>
  );
}

function FlowBar({ pct }) {
  if (pct == null) return null;
  const clamped = Math.max(0, Math.min(150, pct));
  const isLow = pct < 60;
  const color = isLow ? "#f87171" : pct > 110 ? "#fbbf24" : "#34d399";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
      <div
        style={{
          flex: 1,
          height: 8,
          background: "#1a2640",
          borderRadius: 3,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            width: `${(clamped / 150) * 100}%`,
            background: color,
            transition: "width 0.3s",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `${(100 / 150) * 100}%`,
            width: 1,
            background: "#d1dcec88",
          }}
          title="100% design"
        />
      </div>
      <span
        className="mono"
        style={{ fontSize: 13, fontWeight: 700, color, minWidth: 40, textAlign: "right" }}
      >
        {pct}%
      </span>
    </div>
  );
}

function LeaderInputsBlock({ peerSpeeches }) {
  // Renders the EXACT peer JSON the leader was fed. Audit-proof: any decision
  // the leader makes must be derivable from these rows — if not, the LLM is
  // hallucinating and the judge can see it.
  if (!peerSpeeches || peerSpeeches.length === 0) return null;
  return (
    <div
      style={{
        background: "#0a1224",
        border: "1px solid #22d3ee44",
        borderRadius: 4,
        padding: "5px 7px",
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 9,
          color: "#22d3ee",
          letterSpacing: "0.12em",
          fontWeight: 700,
          marginBottom: 2,
        }}
      >
        ▼ INPUTS · {peerSpeeches.length} PEER REPORT{peerSpeeches.length === 1 ? "" : "S"}
      </div>
      {peerSpeeches.map((sp) => {
        const impaired = sp.status === "impaired";
        return (
          <div
            key={sp.valve_id}
            className="mono"
            style={{
              fontSize: 11,
              display: "grid",
              gridTemplateColumns: "30px 60px 40px 62px 1fr",
              gap: 5,
              alignItems: "center",
              color: impaired ? "#f87171" : "#9aacc8",
              padding: "1px 0",
            }}
          >
            <span style={{ fontWeight: 700, color: "#fff" }}>{sp.valve_id}</span>
            <span style={{ fontWeight: 700 }}>
              {(sp.status ?? "—").toUpperCase()}
            </span>
            <span style={{ fontWeight: 700 }}>
              {sp.flow_pct != null ? `${sp.flow_pct}%` : "—"}
            </span>
            <span
              style={{
                color: REQUEST_COLOR[sp.request] ?? "#9aacc8",
                fontWeight: 700,
              }}
            >
              {REQUEST_LABEL[sp.request] ?? "—"}
            </span>
            <span
              style={{
                fontStyle: "italic",
                color: "#d1dcec",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              "{sp.reason ?? sp.text ?? ""}"
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ValveBubble({ vid, speech, isLeader, isActive, isDone, isCached, allocPct, leaderText, leaderPhase, peerSpeeches }) {
  const accent = isLeader ? "#22d3ee" : "#a78bfa";
  const showContent = isActive || isDone || isCached;
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
        opacity: showContent ? 1 : 0.5,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 7, flexShrink: 0, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{ fontSize: 17, fontWeight: 700, color: "#fff", letterSpacing: "0.04em" }}
        >
          {vid}
        </span>
        {isLeader ? (
          <span
            className="mono"
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "#0a1224",
              background: accent,
              padding: "2px 6px",
              borderRadius: 3,
              letterSpacing: "0.1em",
            }}
          >
            LEADER
          </span>
        ) : showContent && speech ? (
          <StatusChip status={speech.status} />
        ) : (
          <span
            className="mono"
            style={{ fontSize: 11, fontWeight: 600, color: accent, letterSpacing: "0.1em" }}
          >
            PEER
          </span>
        )}
        {isActive && (
          <span style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: "auto" }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: accent,
                animation: "debatePulse 0.9s ease-in-out infinite",
              }}
            />
            <span
              className="mono"
              style={{ fontSize: 11, color: accent, fontWeight: 600, letterSpacing: "0.1em" }}
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
              fontSize: 14,
              fontWeight: 700,
              color: accent,
              padding: "2px 7px",
              background: `${accent}1c`,
              borderRadius: 3,
            }}
          >
            → {allocPct.toFixed(0)}%
          </span>
        )}
      </div>
      {isLeader ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 5, minHeight: 95 }}>
          {showContent && <LeaderInputsBlock peerSpeeches={peerSpeeches} />}
          <div
            className="mono"
            style={{
              fontSize: 14,
              color: showContent ? "#d1dcec" : "#445574",
              lineHeight: 1.45,
              minHeight: 50,
              borderTop: showContent ? "1px dashed #2d3d5e" : "none",
              paddingTop: showContent ? 6 : 0,
            }}
          >
            {showContent && (
              <div
                className="mono"
                style={{
                  fontSize: 9,
                  color: leaderPhase === "synth" ? "#fbbf24" : "#34d399",
                  letterSpacing: "0.12em",
                  fontWeight: 700,
                  marginBottom: 3,
                }}
              >
                ▼ DECISION
                {leaderPhase === "synth" && " · weighing inputs…"}
                {leaderPhase === "typing" && " · synthesizing"}
                {leaderPhase === "done" && " · final"}
              </div>
            )}
            {showContent ? leaderText || "…" : "(waiting)"}
            {isActive && leaderPhase !== "synth" && (
              <span
                style={{
                  display: "inline-block",
                  width: 7,
                  height: 14,
                  background: accent,
                  marginLeft: 2,
                  verticalAlign: "text-bottom",
                  animation: "debateCaret 0.6s steps(1) infinite",
                }}
              />
            )}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 5, minHeight: 95 }}>
          {showContent && speech ? (
            <>
              <FlowBar pct={speech.flow_pct} />
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span
                  className="mono"
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: REQUEST_COLOR[speech.request] ?? "#9aacc8",
                    background: `${REQUEST_COLOR[speech.request] ?? "#9aacc8"}1c`,
                    border: `1px solid ${REQUEST_COLOR[speech.request] ?? "#9aacc8"}55`,
                    padding: "2px 7px",
                    borderRadius: 3,
                    letterSpacing: "0.08em",
                  }}
                >
                  {REQUEST_LABEL[speech.request] ?? speech.request ?? "—"}
                </span>
              </div>
              <div
                style={{
                  fontSize: 13,
                  color: "#d1dcec",
                  fontStyle: "italic",
                  lineHeight: 1.35,
                  overflow: "hidden",
                }}
              >
                "{speech.reason ?? speech.text ?? ""}"
              </div>
            </>
          ) : (
            <div
              className="mono"
              style={{ fontSize: 13, color: "#445574", fontStyle: "italic" }}
            >
              (waiting)
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// One row in the multi-round transcript. Renders a peer report (with status
// chip + flow), a leader probe (with @target arrow), an ack, or a final
// decision (gold star). Active row gets typewriter caret + accent halo.
function ConversationBubble({ speech, isLeader, isActive, displayedText, leaderId }) {
  const isFinal = speech.is_final;
  const isImpairedReport =
    speech.kind === "report" && speech.status === "impaired";
  const baseColor = isLeader
    ? isFinal
      ? "#34d399"
      : "#22d3ee"
    : isImpairedReport
      ? "#f87171"
      : "#9aacc8";
  return (
    <div
      style={{
        display: "flex",
        gap: 6,
        alignItems: "flex-start",
        padding: "3px 6px 3px 7px",
        borderLeft: `3px solid ${baseColor}`,
        background: isActive ? `${baseColor}1c` : "transparent",
        borderRadius: 3,
        transition: "background 0.2s",
      }}
    >
      <span
        className="mono"
        style={{ fontWeight: 700, color: "#fff", minWidth: 26, fontSize: 12 }}
      >
        {speech.valve_id}
      </span>
      {speech.kind === "report" && (
        <span
          className="mono"
          style={{
            fontSize: 10,
            color: baseColor,
            fontWeight: 700,
            letterSpacing: "0.06em",
            whiteSpace: "nowrap",
          }}
        >
          {(speech.status ?? "—").toUpperCase()} · {speech.flow_pct ?? "?"}% ·{" "}
          {REQUEST_LABEL[speech.request] ?? "—"}
        </span>
      )}
      {speech.target && (
        <span
          className="mono"
          style={{ fontSize: 11, color: "#9aacc8", fontWeight: 700 }}
        >
          → {speech.target}
        </span>
      )}
      {isFinal && (
        <span
          className="mono"
          style={{
            fontSize: 9,
            color: "#0a1224",
            background: "#34d399",
            padding: "1px 5px",
            borderRadius: 2,
            fontWeight: 700,
            letterSpacing: "0.1em",
          }}
        >
          ★ DECISION
        </span>
      )}
      <span
        style={{
          fontSize: 12,
          color: "#d1dcec",
          fontStyle: "italic",
          flex: 1,
          lineHeight: 1.45,
        }}
      >
        "{displayedText}"
        {isActive && (
          <span
            style={{
              display: "inline-block",
              width: 6,
              height: 12,
              background: baseColor,
              marginLeft: 2,
              verticalAlign: "text-bottom",
              animation: "debateCaret 0.6s steps(1) infinite",
            }}
          />
        )}
      </span>
    </div>
  );
}

function ConversationView({ debate, animState }) {
  const { revealedIdx = -1, activeText = "" } = animState ?? {};
  const speeches = debate.speeches ?? [];
  // Group by round so we can render separators between bursts.
  const byRound = {};
  speeches.forEach((s, i) => {
    const r = s.round ?? 1;
    (byRound[r] = byRound[r] ?? []).push({ speech: s, idx: i });
  });
  const rounds = Object.keys(byRound)
    .map((r) => Number(r))
    .sort((a, b) => a - b);
  const lastIdx = speeches.length - 1;
  const allDone =
    revealedIdx === -1 || revealedIdx >= lastIdx + 1;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {rounds.map((r) => {
        const items = byRound[r];
        const anyRevealed = items.some(
          ({ idx }) => debate.cached || revealedIdx >= idx,
        );
        if (!anyRevealed) return null;
        const isDecision = items.some(({ speech }) => speech.kind === "decide");
        return (
          <div
            key={r}
            style={{ display: "flex", flexDirection: "column", gap: 3 }}
          >
            <div
              className="mono"
              style={{
                fontSize: 9,
                color: isDecision ? "#34d399" : "#445574",
                letterSpacing: "0.16em",
                fontWeight: 700,
                borderBottom: `1px dashed ${isDecision ? "#34d39955" : "#2d3d5e66"}`,
                paddingBottom: 2,
              }}
            >
              ROUND {r}
              {isDecision && " · CONSENSUS"}
            </div>
            {items.map(({ speech, idx }) => {
              const revealed = debate.cached || revealedIdx >= idx;
              const active = !debate.cached && revealedIdx === idx;
              if (!revealed) return null;
              const text = active ? activeText : speech.reason ?? speech.text ?? "";
              return (
                <ConversationBubble
                  key={`${r}-${speech.valve_id}-${idx}`}
                  speech={speech}
                  isLeader={speech.valve_id === debate.leader_id}
                  isActive={active}
                  displayedText={text}
                  leaderId={debate.leader_id}
                />
              );
            })}
          </div>
        );
      })}
      {allDone && debate.allocations && (
        <div
          className="mono"
          style={{
            fontSize: 10,
            color: "#9aacc8",
            padding: "4px 8px",
            background: "#0a1224",
            borderRadius: 3,
            border: "1px solid #2d3d5e",
            display: "flex",
            gap: 10,
            flexWrap: "wrap",
          }}
        >
          <span style={{ color: "#445574", letterSpacing: "0.12em", fontWeight: 700 }}>
            ALLOC
          </span>
          {Object.entries(debate.allocations).map(([k, v]) => (
            <span key={k}>
              {k}={Number(v).toFixed(0)}%
            </span>
          ))}
        </div>
      )}
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
              fontSize: 11,
              color: "#0a1224",
              background: "#a78bfa",
              padding: "2px 7px",
              borderRadius: 3,
              fontWeight: 700,
              letterSpacing: "0.1em",
            }}
          >
            L3
          </span>
          <span
            className="mono"
            style={{ fontSize: 14, color: "#a78bfa", fontWeight: 700, letterSpacing: "0.1em" }}
          >
            BRANCH {branchId}
          </span>
          <span
            className="mono"
            style={{ fontSize: 12, color: "#9aacc8", marginLeft: "auto", fontStyle: "italic" }}
          >
            idle
          </span>
        </div>
        <div
          className="mono"
          style={{
            fontSize: 13,
            color: "#9aacc8",
            fontStyle: "italic",
            padding: "12px 8px",
            textAlign: "center",
          }}
        >
          no debate fired yet on branch {branchId}
        </div>
      </div>
    );
  }

  // Index speeches by valve_id — each speech is a structured dict.
  const speechByValve = Object.fromEntries(
    debate.speeches.map((s) => [s.valve_id, s]),
  );
  const branchValves = VALVES.filter((v) => v.branch === debate.branch_id).map(
    (v) => v.id,
  );
  const peerIds = branchValves.filter((vid) => vid !== debate.leader_id);
  const phases = [
    ...peerIds.map((vid) => ({
      vid,
      speech: speechByValve[vid] ?? null,
      isLeader: false,
    })),
    { vid: debate.leader_id, isLeader: true },
  ];

  const { activeIdx = -1, leaderDisplayed = "", leaderPhase = "done" } = animState ?? {};
  const peerSpeechList = peerIds
    .map((vid) => speechByValve[vid])
    .filter(Boolean);
  // Multi-round = any speech carries a `round` field. Renders as transcript.
  const isMultiRound = debate.speeches?.some((s) => s.round != null);

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
        <span className="mono" style={{ fontSize: 12, color: "#9aacc8", marginLeft: "auto" }}>
          t={debate.tick} · {(debate.wall_clock_s ?? 0).toFixed(2)}s
          {isMultiRound && ` · ${debate.speeches.length} turns`}
          {debate.cached && " · CACHED"}
          {(activeIdx >= 0 || (animState?.revealedIdx ?? -1) >= 0) && " · LIVE"}
        </span>
      </div>

      {isMultiRound ? (
        <ConversationView debate={debate} animState={animState} />
      ) : (
        <div style={{ display: "flex", gap: 5, alignItems: "stretch" }}>
          {phases.map((phase, i) => (
            <ValveBubble
              key={phase.vid}
              vid={phase.vid}
              speech={phase.speech}
              leaderText={phase.isLeader ? leaderDisplayed : undefined}
              leaderPhase={phase.isLeader ? leaderPhase : undefined}
              peerSpeeches={phase.isLeader ? peerSpeechList : undefined}
              isLeader={phase.isLeader}
              isActive={activeIdx === i}
              isDone={activeIdx > i || activeIdx === -1}
              isCached={debate.cached}
              allocPct={phase.isLeader ? null : debate.allocations?.[phase.vid]}
            />
          ))}
        </div>
      )}

    </div>
  );
}

function RecoveryBar({ remediation, debates }) {
  if (!remediation) return null;
  const branchOf = VALVES.find((v) => v.id === remediation.target_valve_id)?.branch;
  // Audit trail: find the most recent debate speech for the target valve from
  // the store, render it as the evidence that drove this decision. If the
  // leader's rationale conflicts with this row, the judge sees the gap.
  const targetSpeech = (() => {
    if (!debates || !remediation.target_valve_id) return null;
    for (let i = debates.length - 1; i >= 0; i--) {
      const d = debates[i];
      const found = d.speeches?.find(
        (s) => s.valve_id === remediation.target_valve_id,
      );
      if (found) return { speech: found, tick: d.tick };
    }
    return null;
  })();
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 5,
        padding: "5px 10px",
        background: `${remediation.executed ? "#34d399" : "#fbbf24"}1c`,
        border: `1.5px solid ${remediation.executed ? "#34d399" : "#fbbf24"}`,
        borderRadius: 5,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
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
      {targetSpeech && (
        <div
          className="mono"
          style={{
            fontSize: 11,
            color: "#d1dcec",
            background: "#0a1224aa",
            border: "1px dashed #34d39955",
            borderRadius: 3,
            padding: "4px 7px",
            display: "flex",
            alignItems: "center",
            gap: 6,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontSize: 9,
              color: "#34d399",
              fontWeight: 700,
              letterSpacing: "0.12em",
            }}
          >
            EVIDENCE →
          </span>
          <span style={{ fontWeight: 700, color: "#fff" }}>
            {remediation.target_valve_id}
          </span>
          <span
            style={{
              fontWeight: 700,
              color:
                targetSpeech.speech.status === "impaired"
                  ? "#f87171"
                  : "#34d399",
            }}
          >
            {(targetSpeech.speech.status ?? "—").toUpperCase()}
          </span>
          <span style={{ fontWeight: 700 }}>
            {targetSpeech.speech.flow_pct != null
              ? `${targetSpeech.speech.flow_pct}%`
              : "—"}
          </span>
          <span
            style={{
              color: REQUEST_COLOR[targetSpeech.speech.request] ?? "#9aacc8",
              fontWeight: 700,
            }}
          >
            {REQUEST_LABEL[targetSpeech.speech.request] ?? "—"}
          </span>
          <span style={{ fontStyle: "italic", color: "#9aacc8" }}>
            "{targetSpeech.speech.reason ?? targetSpeech.speech.text ?? ""}"
          </span>
          <span style={{ color: "#445574", marginLeft: "auto" }}>
            from debate @ t={targetSpeech.tick}s
          </span>
        </div>
      )}
    </div>
  );
}

export default function DebateStage() {
  const debates = useDashboardStore((s) => s.debates);
  const latestRemediation = useDashboardStore((s) => s.latestRemediation);
  const [collapsed, setCollapsed] = useState(false);

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
        setAnimByBranch((prev) => ({
          ...prev,
          [branchId]: {
            activeIdx: -1,
            leaderDisplayed: latest.rationale,
            leaderPhase: "done",
            revealedIdx: -1,
          },
        }));
        continue;
      }

      // Multi-round transcript path — speeches carry a `round` field. Reveal
      // sequentially with mini-typewriter on each speech's reason.
      const isMulti = latest.speeches?.some((s) => s.round != null);
      if (isMulti) {
        const speeches = latest.speeches;
        let sIdx = 0;
        setAnimByBranch((prev) => ({
          ...prev,
          [branchId]: { revealedIdx: 0, activeText: "" },
        }));
        const CHAR_CONV_MS = 28;
        const INTER_BUBBLE_MS = 600;
        const advanceBubble = () => {
          if (sIdx >= speeches.length) {
            setAnimByBranch((prev) => ({
              ...prev,
              [branchId]: { ...prev[branchId], revealedIdx: speeches.length, activeText: "" },
            }));
            return;
          }
          const text = speeches[sIdx].reason ?? speeches[sIdx].text ?? "";
          let cIdx = 0;
          setAnimByBranch((prev) => ({
            ...prev,
            [branchId]: { ...prev[branchId], revealedIdx: sIdx, activeText: "" },
          }));
          const typeBubble = () => {
            if (cIdx > text.length) {
              timersRef.current[branchId] = setTimeout(() => {
                sIdx++;
                advanceBubble();
              }, INTER_BUBBLE_MS);
              return;
            }
            setAnimByBranch((prev) => ({
              ...prev,
              [branchId]: { ...prev[branchId], activeText: text.slice(0, cIdx) },
            }));
            cIdx++;
            timersRef.current[branchId] = setTimeout(typeBubble, CHAR_CONV_MS);
          };
          typeBubble();
        };
        advanceBubble();
        continue;
      }

      // Single-round path (legacy 2-section layout for LIVE debates):
      //   1. Each peer bubble flashes for PHASE_PAUSE_MS (structured JSON reveal)
      //   2. Leader phase "synth": INPUTS block visible, decision text shows
      //      "weighing inputs…", LEADER_SYNTH_PAUSE_MS pause so judges read
      //      the inputs the LLM was fed (audit-proof against hallucination)
      //   3. Leader phase "typing": typewrite the rationale at CHAR_DELAY_MS
      //   4. After typing, brief pause then de-activate
      const branchValves = VALVES.filter((v) => v.branch === branchId).map((v) => v.id);
      const peerIds = branchValves.filter((vid) => vid !== latest.leader_id);
      const totalPhases = peerIds.length + 1;
      const leaderIdx = peerIds.length;

      let pIdx = 0;
      setAnimByBranch((prev) => ({
        ...prev,
        [branchId]: { activeIdx: 0, leaderDisplayed: "", leaderPhase: "done" },
      }));

      const step = () => {
        if (pIdx >= totalPhases) {
          setAnimByBranch((prev) => ({
            ...prev,
            [branchId]: { ...prev[branchId], activeIdx: -1, leaderPhase: "done" },
          }));
          return;
        }
        if (pIdx < leaderIdx) {
          // Peer phase — flash the bubble briefly, then advance.
          timersRef.current[branchId] = setTimeout(() => {
            pIdx++;
            setAnimByBranch((prev) => ({
              ...prev,
              [branchId]: { ...prev[branchId], activeIdx: pIdx },
            }));
            step();
          }, PHASE_PAUSE_MS);
          return;
        }
        // Leader phase. First: synthesis pause — INPUTS block visible, no
        // typewriter yet. Judges see the JSON inputs the leader was fed.
        setAnimByBranch((prev) => ({
          ...prev,
          [branchId]: {
            ...prev[branchId],
            leaderDisplayed: "",
            leaderPhase: "synth",
          },
        }));
        timersRef.current[branchId] = setTimeout(() => {
          // Phase 3: typewriter the rationale.
          const text = latest.rationale ?? "";
          let cIdx = 0;
          setAnimByBranch((prev) => ({
            ...prev,
            [branchId]: { ...prev[branchId], leaderPhase: "typing" },
          }));
          const typeLeader = () => {
            if (cIdx > text.length) {
              setAnimByBranch((prev) => ({
                ...prev,
                [branchId]: { ...prev[branchId], leaderPhase: "done" },
              }));
              timersRef.current[branchId] = setTimeout(() => {
                setAnimByBranch((prev) => ({
                  ...prev,
                  [branchId]: { ...prev[branchId], activeIdx: -1 },
                }));
              }, PHASE_PAUSE_MS);
              return;
            }
            setAnimByBranch((prev) => ({
              ...prev,
              [branchId]: { ...prev[branchId], leaderDisplayed: text.slice(0, cIdx) },
            }));
            cIdx++;
            timersRef.current[branchId] = setTimeout(typeLeader, CHAR_DELAY_MS);
          };
          typeLeader();
        }, LEADER_SYNTH_PAUSE_MS);
      };
      step();
    }
    return () => {
      for (const t of Object.values(timersRef.current)) clearTimeout(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debates]);

  const totalTurns = debates.reduce(
    (n, d) => n + (d.speeches?.length ?? 0),
    0,
  );
  const activeBranches = BRANCHES.filter((b) => latestByBranch[b]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minHeight: 0,
      }}
    >
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="mono"
        aria-expanded={!collapsed}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "4px 10px",
          background: collapsed ? "#0f1a30" : "#131f37",
          border: "1px solid #2d3d5e",
          borderRadius: 5,
          color: "#a78bfa",
          fontFamily: "monospace",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.12em",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 12,
            textAlign: "center",
            transition: "transform 0.15s",
            transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)",
          }}
        >
          ▼
        </span>
        <span
          style={{
            color: "#0a1224",
            background: "#a78bfa",
            padding: "1px 6px",
            borderRadius: 2,
            fontSize: 10,
          }}
        >
          L3
        </span>
        <span>MULTI-AGENT DEBATE</span>
        <span style={{ color: "#9aacc8", fontWeight: 400, letterSpacing: "0.06em" }}>
          {debates.length === 0
            ? "· no debates yet"
            : `· ${debates.length} debate${debates.length === 1 ? "" : "s"} · ${totalTurns} turns · branch ${activeBranches.join(", ")}`}
        </span>
        {latestRemediation && (
          <span
            style={{
              marginLeft: "auto",
              color: latestRemediation.executed ? "#34d399" : "#fbbf24",
              fontSize: 10,
              letterSpacing: "0.1em",
            }}
          >
            {latestRemediation.executed ? "✓" : "•"} last action:{" "}
            {(latestRemediation.action ?? "").replaceAll("_", " ").toUpperCase()}{" "}
            on {latestRemediation.target_valve_id}
          </span>
        )}
      </button>
      {!collapsed && (
        <>
          <RecoveryBar remediation={latestRemediation} debates={debates} />
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
        </>
      )}
      <style>{`
        @keyframes debatePulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.7); } }
        @keyframes debateCaret { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
      `}</style>
    </div>
  );
}
