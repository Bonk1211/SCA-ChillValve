import { useEffect, useRef, useState } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useDashboardStore } from "./store/useDashboardStore";
import { api } from "./lib/api";
import {
  SCENARIOS,
  SCENARIO_BY_ID,
  reverseScenarioLookup,
  runScenario,
} from "./components/v5/scenarios";
import TitleBar from "./components/v5/TitleBar";
import ScenarioPicker from "./components/v5/ScenarioPicker";
import KpiTrio from "./components/v5/KpiTrio";
import FlowChart from "./components/v5/FlowChart";
import Schematic from "./components/v5/Schematic";
import ValveTable from "./components/v5/ValveTable";
import EventLog from "./components/v5/EventLog";
import DebateStage from "./components/v5/DebateStage";
import SummaryBanner from "./components/v5/SummaryBanner";
import ControlBar from "./components/v5/ControlBar";
import Landing from "./components/landing/Landing";

// Hash-based view switcher. "#/simulator" → SimulatorApp; otherwise Landing.
// Kept simple instead of pulling in react-router for a single transition.
function readView() {
  return typeof window !== "undefined" && window.location.hash === "#/simulator"
    ? "simulator"
    : "landing";
}

export default function App() {
  const [view, setView] = useState(readView);
  useEffect(() => {
    const onHash = () => setView(readView());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const enterSimulator = () => {
    window.location.hash = "#/simulator";
    setView("simulator");
  };
  return view === "simulator"
    ? <SimulatorApp />
    : <Landing onEnter={enterSimulator} />;
}

const POLL_HEALTH_MS = 2000;

function SidebarHandle({ side, open, onToggle, label }) {
  const isLeft = side === "left";
  // When open, sit at sidebar's inner edge (right for left-bar, left for right-bar).
  // When closed, fill the whole 22px slot.
  const arrowOpen = isLeft ? "‹" : "›";
  const arrowClosed = isLeft ? "›" : "‹";
  return (
    <button
      onClick={onToggle}
      title={open ? `hide ${label}` : `show ${label}`}
      className="mono"
      style={{
        gridColumn: open ? (isLeft ? "2 / 3" : "1 / 2") : "1 / -1",
        gridRow: "1 / -1",
        background: "#131f37",
        border: "1px solid #2d3d5e",
        borderRadius: 4,
        color: "#9aacc8",
        cursor: "pointer",
        padding: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        fontSize: 14,
        fontWeight: 700,
        writingMode: "vertical-rl",
        textOrientation: "mixed",
        transition: "background 0.15s, color 0.15s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "#1a2640";
        e.currentTarget.style.color = "#22d3ee";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "#131f37";
        e.currentTarget.style.color = "#9aacc8";
      }}
    >
      <span style={{ writingMode: "horizontal-tb", fontSize: 14, lineHeight: 1 }}>
        {open ? arrowOpen : arrowClosed}
      </span>
      <span style={{ fontSize: 9, letterSpacing: "0.14em" }}>{label}</span>
    </button>
  );
}

function SimulatorApp() {
  useWebSocket("ws://localhost:8000/ws");
  const connection = useDashboardStore((s) => s.connection);
  const engineStatus = useDashboardStore((s) => s.engineStatus);
  const setEngineStatus = useDashboardStore((s) => s.setEngineStatus);
  const addEvent = useDashboardStore((s) => s.addEvent);

  const [currentScenarioId, setCurrentScenarioId] = useState(null);
  const [selectedValveId, setSelectedValveId] = useState("B2");
  const [busy, setBusy] = useState(false);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  // Synchronous busy guard — React state takes a commit cycle to propagate, so
  // a rapid double-click on START can fire two pickScenario before the first
  // setBusy(true) renders. This ref updates atomically.
  const busyRef = useRef(false);

  const LEFT_OPEN_W = 300;
  const RIGHT_OPEN_W = 420;
  const COLLAPSED_W = 22;

  useEffect(() => {
    const tick = async () => {
      try {
        const h = await api.health();
        setEngineStatus(h);
        // Hydrate currentScenarioId from backend on first connect / browser
        // refresh — otherwise the ScenarioBanner shows empty state while the
        // engine is actively running a scenario picked in a prior session.
        if (
          h.scenario &&
          SCENARIO_BY_ID[reverseScenarioLookup(h.scenario)] &&
          currentScenarioId == null
        ) {
          setCurrentScenarioId(reverseScenarioLookup(h.scenario));
        }
      } catch {
        /* backend down — ignore */
      }
    };
    tick();
    const id = setInterval(tick, POLL_HEALTH_MS);
    return () => clearInterval(id);
  }, [setEngineStatus, currentScenarioId]);

  const pickScenario = async (id) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      useDashboardStore.getState().reset();
      const s = await runScenario(id);
      setCurrentScenarioId(id);
      addEvent("ctrl", `scenario started · ${s.label} (${s.backendName})`);
    } catch (e) {
      addEvent("rule", `scenario start failed: ${e?.message ?? e}`);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const handleReplay = async () => {
    if (busyRef.current || !currentScenarioId) return;
    await pickScenario(currentScenarioId);
  };

  const handleStart = async () => {
    if (busyRef.current) return;
    if (engineStatus.engine === "paused") {
      busyRef.current = true;
      setBusy(true);
      try {
        await api.resume();
        addEvent("ctrl", "engine resumed");
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
      return;
    }
    if (engineStatus.engine === "idle") {
      // Default to the first scenario if user hasn't picked one yet — keeps
      // the prominent green START button from looking broken on first load.
      const targetId = currentScenarioId || SCENARIOS[0]?.id;
      if (targetId) await pickScenario(targetId);
    }
  };

  const handleStop = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      await api.pause();
      addEvent("ctrl", "engine paused");
    } catch (e) {
      addEvent("rule", `stop failed: ${e?.message ?? e}`);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        background: "#0a1224",
        color: "#fff",
        fontFamily: "Inter, system-ui, sans-serif",
        fontSize: 14,
      }}
    >
      <TitleBar
        connection={connection}
        engineStatus={engineStatus}
      />
      <ScenarioPicker
        currentId={currentScenarioId}
        onPick={pickScenario}
        busy={busy}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `${leftOpen ? LEFT_OPEN_W : COLLAPSED_W}px 1fr ${rightOpen ? RIGHT_OPEN_W : COLLAPSED_W}px`,
          flex: 1,
          minHeight: 0,
          padding: 8,
          gap: 8,
          transition: "grid-template-columns 0.2s ease",
        }}
      >
        {/* LEFT SIDEBAR — KPIs + per-valve flow cards (scrollable) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: leftOpen ? "1fr 22px" : "22px",
            gap: leftOpen ? 6 : 0,
            minWidth: 0,
            minHeight: 0,
            overflow: "hidden",
            position: "relative",
          }}
        >
          {leftOpen && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                minWidth: 0,
                minHeight: 0,
                overflowY: "auto",
                overflowX: "hidden",
                paddingRight: 2,
              }}
            >
              <KpiTrio />
              <FlowChart
                selectedValveId={selectedValveId}
                onSelectValve={setSelectedValveId}
              />
            </div>
          )}
          <SidebarHandle
            side="left"
            open={leftOpen}
            onToggle={() => setLeftOpen((v) => !v)}
            label="KPIs · Flow"
          />
        </div>

        {/* CENTER — schematic on top, debate stage below */}
        <div
          style={{
            display: "grid",
            gridTemplateRows: "1fr auto",
            gap: 6,
            minWidth: 0,
            minHeight: 0,
            overflow: "hidden",
          }}
        >
        <div
          style={{
            background: "#0f1a30",
            border: "1px solid #2d3d5e",
            borderRadius: 6,
            padding: 6,
            minHeight: 0,
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 4,
              flexShrink: 0,
            }}
          >
            <span
              className="mono"
              style={{
                fontSize: 10,
                color: "#fff",
                fontWeight: 700,
                letterSpacing: "0.1em",
              }}
            >
              HYDRAULIC SCHEMATIC · LIVE
            </span>
            <div
              style={{
                display: "flex",
                gap: 8,
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 9,
                color: "#9aacc8",
              }}
            >
              <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#34d399", verticalAlign: "middle", marginRight: 4 }} />healthy</span>
              <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#fbbf24", verticalAlign: "middle", marginRight: 4 }} />anomaly</span>
              <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#f87171", verticalAlign: "middle", marginRight: 4 }} />safety-override</span>
              <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#22d3ee", verticalAlign: "middle", marginRight: 4, boxShadow: "0 0 4px #22d3ee" }} />leader</span>
            </div>
          </div>
          <div style={{ flex: 1, minHeight: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Schematic
              selectedValveId={selectedValveId}
              onSelectValve={setSelectedValveId}
            />
          </div>
        </div>
        <SummaryBanner />
        <DebateStage />
        </div>

        {/* RIGHT — valve table + event log */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: rightOpen ? "22px 1fr" : "22px",
            gridTemplateRows: rightOpen ? "auto 1fr" : "1fr",
            gap: rightOpen ? 8 : 0,
            minWidth: 0,
            minHeight: 0,
            overflow: "hidden",
            position: "relative",
          }}
        >
          <SidebarHandle
            side="right"
            open={rightOpen}
            onToggle={() => setRightOpen((v) => !v)}
            label="Valves · Events"
          />
          {rightOpen && (
            <>
              <div style={{ minHeight: 0, minWidth: 0 }}>
                <ValveTable selectedId={selectedValveId} onSelect={setSelectedValveId} />
              </div>
              <div
                style={{
                  minHeight: 0,
                  minWidth: 0,
                  gridColumn: "2 / 3",
                  display: "grid",
                  gridTemplateRows: "1fr 1fr 1.4fr",
                  gap: 5,
                }}
              >
                <EventLog
                  title="RULES · L1"
                  layerBadge="L1"
                  accent="#f87171"
                  kinds={["rule", "fault"]}
                  emptyText="no Layer-1 rules fired"
                />
                <EventLog
                  title="ML ANOMALY · L2"
                  layerBadge="L2"
                  accent="#fbbf24"
                  kinds={["anomaly"]}
                  emptyText="no Layer-2 anomalies"
                />
                <EventLog
                  title="COORDINATION · L3"
                  layerBadge="L3"
                  accent="#a78bfa"
                  kinds={["debate", "remediation", "leader", "election", "ctrl", "story"]}
                  emptyText="no Layer-3 coordination events"
                />
              </div>
            </>
          )}
        </div>
      </div>

      <ControlBar
        onReplay={handleReplay}
        onStart={handleStart}
        onStop={handleStop}
        busy={busy}
        engineState={engineStatus.engine}
        canReplay={currentScenarioId != null}
      />
    </div>
  );
}
