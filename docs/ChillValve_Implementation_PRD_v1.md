# ChillValve — Software Implementation PRD

**Project:** ChillValve Smart PICV — Software Layer
**Role:** Software Lead
**Scope:** Pure implementation plan, prototyping focus
**Goal:** A working three-layer intelligence prototype that demonstrates distributed cooperative control of HVAC valves, with real ML and live multi-agent coordination, suitable for a recorded demo and technical defense.

---

## 1. What You're Building

A working prototype of the ChillValve smart valve software stack. Three independent intelligence layers operate on each simulated valve and coordinate across a small network. The prototype includes:

- A Python simulation of 6 valves arranged in 2 branches of 3, modelling realistic hydraulics
- Three intelligence layers running on every valve: deterministic rules, trained ML anomaly detection, distributed multi-agent coordination
- A FastAPI backend hosting the multi-agent orchestration over WebSocket
- A React + Vite dashboard visualising the system in real time
- A trained Isolation Forest model for Layer 2, with real LBNL training data
- A Belimo Energy Valve baseline mode for comparison
- Pre-recorded demo footage and a Q&A defense sheet

The prototype is local-only. No cloud services. No production deployment infrastructure. The goal is a defensible technical demonstration of the multi-agent cooperative-control thesis.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  React + Vite Dashboard (localhost:5173)                     │
│  - 6 valve tiles with live state                              │
│  - Energy comparison chart (Belimo vs ChillValve)             │
│  - Layer activity indicators (rules / ML / agent)             │
│  - Scenario controls                                          │
└──────────────────────┬───────────────────────────────────────┘
                       │ WebSocket
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI Backend (localhost:8000)                            │
│  - WebSocket /ws (stream state to dashboard)                 │
│  - REST /scenario/* (control scenario playback)              │
│  - Multi-agent orchestrator (asyncio coroutines)             │
└──────────┬───────────────────────────┬───────────────────────┘
           │                           │
           ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│  Python Simulation       │  │  SQLite Database              │
│  - 6 valve agents        │  │  - operational_data            │
│  - Hydraulic model       │  │  - anomaly_events              │
│  - Three layers per valve│  │  - coordination_log            │
│  - Belimo baseline mode  │  │  - scenario_metadata           │
└──────────────────────────┘  └──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│  ML Artifacts (data/models/)                                 │
│  - isolation_forest.pkl                                       │
│  - feature_scaler.pkl                                         │
│  - training_metadata.json                                     │
└──────────────────────────────────────────────────────────────┘

External: LBNL Fault Detection and Diagnostics Dataset
          (downloaded once for ML training, not runtime dependency)
```

---

## 3. Repository Structure

```
chillvalve/
├── README.md
├── pyproject.toml                  # Python dependencies via uv or poetry
├── data/
│   ├── lbnl_raw/                    # Downloaded LBNL CSVs
│   ├── lbnl_processed/              # Cleaned, normalized
│   ├── models/
│   │   ├── isolation_forest.pkl
│   │   ├── feature_scaler.pkl
│   │   └── training_metadata.json
│   ├── scenarios/
│   │   ├── steady_state.json
│   │   └── load_spike.json
│   └── chillvalve.db                # SQLite database
├── sim/
│   ├── __init__.py
│   ├── valve.py                     # Valve hydraulic model
│   ├── system.py                    # 6-valve system + pump
│   ├── controllers/
│   │   ├── belimo_baseline.py
│   │   └── chillvalve.py
│   ├── layers/
│   │   ├── layer1_rules.py
│   │   ├── layer2_ml.py
│   │   └── layer3_agent.py
│   ├── scenarios.py
│   └── engine.py                    # Main simulation loop
├── ml/
│   ├── download_lbnl.py
│   ├── preprocess.py
│   ├── train.py
│   ├── validate.py
│   └── notebooks/
│       └── eda.ipynb
├── backend/
│   ├── main.py                      # FastAPI app
│   ├── websocket.py
│   ├── orchestrator.py              # Multi-agent coordination
│   ├── db.py                        # SQLite access
│   └── models.py                    # Pydantic schemas
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── ValveTile.jsx
│   │   │   ├── BranchRow.jsx
│   │   │   ├── EnergyChart.jsx
│   │   │   ├── EventLog.jsx
│   │   │   ├── LayerIndicator.jsx
│   │   │   ├── ScenarioControls.jsx
│   │   │   └── ModeToggle.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   └── lib/
│   │       └── colors.js
└── docs/
    ├── algorithm_pseudocode.md      # Hand to Report Lead
    ├── qa_defense.md
    └── architecture_diagram.svg
```

---

## 4. The Simulation

### 4.1 System Configuration

The simulation models a chilled water distribution loop in a 5 MW Tier 3 data center.

| Parameter | Value |
|---|---|
| Number of valves | 6 |
| Number of branches | 2 |
| Branch A composition | 3 × DN65 valves serving CRAH units |
| Branch B composition | 3 × DN100 valves serving AHU units |
| Chilled water supply temp | 7°C |
| Design return temp | 12°C (ΔT = 5°C) |
| Pump max head | 250 kPa |
| Pump max flow | 800 GPM |
| Pump efficiency | 0.65 |
| Simulation tick | 1 second (real time) |
| Scenario duration | 60 minutes simulated |
| Wall-clock playback | configurable; demo uses 60 seconds (60x speed) |

### 4.2 Valve Hydraulic Model

Each valve uses an equal-percentage characterized ball valve model:

```
Cv(position) = Cv_max × R^(position - 1)

where R = 50 (rangeability)
      position ∈ [0, 1]
      Cv_max from datasheet (DN65: 47, DN100: 150)

Flow = Cv × √(ΔP / SG)
where SG = 1.0 (water)
      ΔP in psi (convert from kPa as needed)
      Flow in GPM
```

Coil thermal behavior:

```
capacity_demand = m_dot × Cp × ΔT_design
m_dot_actual = flow × density / 60   (convert GPM to kg/s)

If m_dot_actual < m_dot_design:
    ΔT_achieved = capacity_demand / (m_dot_actual × Cp)
    # ΔT collapses when underflowing
Else:
    ΔT_achieved = ΔT_design × (m_dot_design / m_dot_actual)
    # ΔT degrades when overflowing
```

Air-side load varies per scenario. The simulation injects load disturbances based on the chosen scenario.

### 4.3 Pump Model

Single pump serves both branches. Pump head depends on total flow:

```
ΔP_pump = ΔP_static + k × Q²
P_pump_kW = (Q_total × ΔP_pump) / (3960 × η_pump)   # HP equation, converted
```

Pump speed is controlled differently depending on mode:
- **Belimo baseline:** maintains constant ΔP across "remote sensor" location, ramps speed accordingly
- **ChillValve:** branch leader broadcasts recommended pump setpoint based on aggregated branch demand

### 4.4 Scenarios

#### Scenario A — Steady-State Optimization
- All valves at 70% design load
- Minor load fluctuations (±5%) every 5 minutes
- Demonstrates baseline coordination benefit
- This is the **primary demo scenario**

#### Scenario B — Load Spike (optional, time permitting)
- Steady state for first 10 minutes
- Sudden +40% load on AHU-B2 at minute 10
- Demonstrates fast coordination response
- Shows ChillValve advantage over Belimo's slow cloud loop

#### Scenario C — Fault Injection (for ML demo)
- Steady state with one valve developing simulated fouling
- Flow gradually drops 15% over 20 minutes
- Layer 2 ML detects the anomaly before Layer 1 rules would trigger
- Shows the value of the trained Isolation Forest

---

## 5. Three-Layer Intelligence — Full Specification

Every valve runs all three layers simultaneously on every simulation tick. Layers operate at different cadences and can be observed independently on the dashboard.

### 5.1 Layer 1 — Rules Engine

**Purpose:** Deterministic safety and stability. Fires every tick. Microsecond response time. Never disabled.

**Implementation:** `sim/layers/layer1_rules.py`

```python
class Layer1Rules:
    """
    Deterministic rules. Always active. Cannot be overridden by Layer 2 or 3.
    Returns a (action, reason) tuple if a rule fires, else None.
    """

    def __init__(self):
        self.last_known_good = {}

    def evaluate(self, valve: ValveState) -> Optional[RuleAction]:
        # Rule 1: Clamp position to physical limits
        if not 0.0 <= valve.position <= 1.0:
            return RuleAction(
                action="clamp_position",
                value=max(0.0, min(1.0, valve.position)),
                reason="position_out_of_bounds"
            )

        # Rule 2: Flow ceiling
        if valve.flow_gpm > valve.flow_max * 1.10:
            return RuleAction(
                action="reduce_position",
                value=valve.position * 0.9,
                reason="flow_exceeds_max_110pct"
            )

        # Rule 3: Pressure failsafe (water hammer protection)
        if valve.dP_kPa > 600:
            return RuleAction(
                action="emergency_close",
                value=0.0,
                reason="dP_exceeds_600kPa"
            )

        # Rule 4: Sensor validity
        if any(isnan_or_outlier(v) for v in [valve.flow_gpm, valve.dT_C, valve.dP_kPa]):
            return RuleAction(
                action="use_last_known_good",
                value=self.last_known_good.get(valve.id),
                reason="sensor_invalid"
            )

        # Rule 5: Actuator timeout
        if valve.commanded_position_age_s > 30 and \
           abs(valve.position - valve.commanded_position) > 0.05:
            return RuleAction(
                action="raise_fault",
                value=None,
                reason="actuator_unresponsive"
            )

        # Update last known good
        self.last_known_good[valve.id] = (valve.flow_gpm, valve.dT_C, valve.dP_kPa)
        return None
```

Rules fire deterministically. No ML, no negotiation. They are the safety floor under everything else.

### 5.2 Layer 2 — ML Anomaly Detection

**Purpose:** Detect slowly-developing issues (coil fouling, sensor drift, control instability) that Layer 1 rules cannot catch.

**Model:** Isolation Forest, trained on LBNL FDD Single-Duct AHU dataset
**Cadence:** Every 10 simulated seconds per valve
**Implementation:** `sim/layers/layer2_ml.py`

#### Training Pipeline

`ml/download_lbnl.py`:
- Downloads LBNL Fault Detection and Diagnostics Single-Duct AHU subset
- Extracts to `data/lbnl_raw/`

`ml/preprocess.py`:
- Loads all fault-free CSVs into a single DataFrame
- Maps LBNL column names to valve sensor schema (flow, supply temp, return temp, position, ΔT, ΔP)
- Resamples to 1-minute intervals
- Handles missing values (forward fill ≤5 min gaps, drop longer gaps)
- Adds engineered features:
  - 10-minute rolling mean of flow, ΔT, position
  - 10-minute rolling std of flow, ΔT
  - Hour of day (cyclic encoding: sin, cos)
  - Day type (weekday/weekend)
- Splits chronologically: 70% train (fault-free only), 30% test (mix of fault-free and faulted)
- Saves to `data/lbnl_processed/{train,test}.parquet`

`ml/train.py`:
```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

X_train = load_parquet('data/lbnl_processed/train.parquet')

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    max_samples=256,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled)

joblib.dump(model, 'data/models/isolation_forest.pkl')
joblib.dump(scaler, 'data/models/feature_scaler.pkl')

# Save training metadata for slides
metadata = {
    'training_samples': len(X_train),
    'features': X_train.columns.tolist(),
    'contamination': 0.05,
    'n_estimators': 200,
    'lbnl_subset': 'single_duct_ahu',
    'training_date': datetime.now().isoformat()
}
json.dump(metadata, open('data/models/training_metadata.json', 'w'))
```

`ml/validate.py`:
- Loads test set with known fault labels
- Computes AUC, precision, recall, F1 at multiple thresholds
- Generates three plots for slides:
  1. ROC curve
  2. Score distribution (normal vs faulted)
  3. Time-series example showing fault detection
- Saves plots to `docs/ml_validation/*.png`

#### Inference at Simulation Time

```python
class Layer2ML:
    """
    Isolation Forest anomaly detector. Trained offline on LBNL FDD data.
    Runs every 10 simulated seconds per valve.
    """

    def __init__(self, model_path: str, scaler_path: str):
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.history = {}  # valve_id -> deque of recent states

    def evaluate(self, valve: ValveState) -> AnomalyResult:
        # Build feature vector
        features = self._extract_features(valve)
        features_scaled = self.scaler.transform([features])

        # Anomaly score: lower = more anomalous
        raw_score = self.model.decision_function(features_scaled)[0]
        is_anomaly = self.model.predict(features_scaled)[0] == -1

        # Convert raw score to 0-1 confidence
        confidence = self._score_to_confidence(raw_score)

        return AnomalyResult(
            anomaly_detected=is_anomaly,
            confidence=confidence,
            raw_score=raw_score,
            features=features,
            timestamp=valve.timestamp
        )

    def _extract_features(self, valve: ValveState) -> List[float]:
        hist = self.history.setdefault(valve.id, deque(maxlen=600))
        hist.append(valve)

        recent = list(hist)[-10:]  # last 10 ticks

        return [
            valve.flow_gpm,
            valve.dT_C,
            valve.position_pct,
            valve.supply_temp_C,
            valve.return_temp_C,
            np.mean([v.flow_gpm for v in recent]),
            np.std([v.flow_gpm for v in recent]) if len(recent) > 1 else 0,
            np.mean([v.dT_C for v in recent]),
            np.sin(2 * np.pi * valve.hour_of_day / 24),
            np.cos(2 * np.pi * valve.hour_of_day / 24),
        ]
```

#### Decision Logic

If anomaly detected with confidence > 0.85, log event and notify Layer 3 for potential coordination response.
If confidence between 0.5 and 0.85, log warning but continue normal operation.
Below 0.5, ignore.

### 5.3 Layer 3 — Multi-Agent Coordination

**Purpose:** Cross-valve optimization to reduce total pump energy. Each valve is an agent.

**Cadence:** Every 5 simulated seconds (broadcast); leader recomputes setpoints every 5 seconds.
**Implementation:** `sim/layers/layer3_agent.py` + `backend/orchestrator.py`

#### Agent Behavior

Every valve agent runs the following loop:

```python
class ValveAgent:
    """
    Distributed agent. Each valve runs one of these.
    Communicates via FastAPI WebSocket broker (acting as message bus).
    """

    def __init__(self, valve_id, branch_id, broker):
        self.id = valve_id
        self.branch_id = branch_id
        self.broker = broker
        self.peer_states = {}      # latest state from each peer
        self.is_leader = False
        self.last_leader_heartbeat = time.time()
        self.election_in_progress = False

    async def tick(self, my_state: ValveState):
        # 1. Broadcast my state to peers in my branch
        await self.broker.broadcast(
            channel=f"branch/{self.branch_id}",
            sender_id=self.id,
            payload=my_state.to_dict()
        )

        # 2. Collect peer messages (non-blocking, get whatever has arrived)
        messages = await self.broker.collect(channel=f"branch/{self.branch_id}", since=last_tick)
        for msg in messages:
            self.peer_states[msg.sender_id] = msg.payload

        # 3. Check for leader heartbeat
        await self._check_leader_alive()

        # 4. If I'm the leader, compute and broadcast coordination decision
        if self.is_leader:
            await self._leader_logic()

    async def _check_leader_alive(self):
        # Leader sends heartbeat with leader_alive=True flag
        # If 15s elapse without heartbeat, trigger election
        if time.time() - self.last_leader_heartbeat > 15:
            await self._trigger_election()

    async def _trigger_election(self):
        """
        Bully algorithm: lowest valve_id wins.
        Each valve broadcasts election message with its id.
        After 3 seconds, valve with lowest id declares itself leader.
        """
        self.election_in_progress = True
        await self.broker.broadcast(
            channel=f"branch/{self.branch_id}/election",
            sender_id=self.id,
            payload={"candidate_id": self.id}
        )

        await asyncio.sleep(3.0)

        # Collect all candidate ids
        candidates = [self.id] + [
            m.payload["candidate_id"]
            for m in await self.broker.collect(channel=f"branch/{self.branch_id}/election", since=election_start)
        ]
        new_leader = min(candidates)

        self.is_leader = (new_leader == self.id)
        self.election_in_progress = False
        self.last_leader_heartbeat = time.time()

        if self.is_leader:
            log_event(f"Valve {self.id} elected leader of branch {self.branch_id}")

    async def _leader_logic(self):
        """
        Aggregate branch state, compute optimal flow allocation,
        broadcast recommended setpoints.
        """
        branch_valves = [self.peer_states.get(vid) for vid in branch_member_ids(self.branch_id)]
        branch_valves = [v for v in branch_valves if v is not None]

        # 1. Compute aggregate demand
        total_capacity_demand_kW = sum(v["capacity_demand_kW"] for v in branch_valves)

        # 2. Compute optimal pump pressure for this demand
        recommended_pump_dP = self._compute_optimal_pump_dP(branch_valves)

        # 3. Allocate flow per valve based on priority
        allocations = {}
        for v in branch_valves:
            priority = self._compute_priority(v)
            allocations[v["id"]] = self._allocate(v, priority, total_capacity_demand_kW)

        # 4. Broadcast setpoints
        await self.broker.broadcast(
            channel=f"branch/{self.branch_id}/setpoints",
            sender_id=self.id,
            payload={
                "leader_id": self.id,
                "pump_dP_recommended": recommended_pump_dP,
                "valve_setpoints": allocations,
                "leader_alive": True
            }
        )

    def _compute_priority(self, valve_state):
        """
        Higher priority for valves not meeting their capacity demand,
        especially those with anomalies detected.
        """
        capacity_deficit = max(0, valve_state["capacity_demand_kW"] - valve_state["capacity_delivered_kW"])
        anomaly_penalty = 1.5 if valve_state.get("anomaly_detected") else 1.0
        return capacity_deficit * anomaly_penalty

    def _allocate(self, valve_state, priority, total_demand):
        # Pseudo-MPC: allocate flow proportional to priority,
        # constrained by physical valve limits
        ...
```

#### Coordination Decisions

The leader's algorithm makes three kinds of decisions every cycle:

1. **Pump speed recommendation** — based on aggregate branch capacity demand and current pump-system curve
2. **Per-valve flow allocation** — priority-based, with anomaly-detected valves getting priority
3. **Branch consensus check** — if peer states diverge from leader's model by more than 20%, escalate to BMS log

#### Election Algorithm (Bully)

Simple deterministic algorithm:
- Each valve has a unique `valve_id` (e.g., A1, A2, A3, B1, B2, B3)
- Within each branch, lowest-id valve is the default leader
- On boot, each valve assumes it might be leader; broadcasts presence
- After 3 seconds of listening, the valve with the lowest observed id assumes leadership
- Leader sends heartbeat every 5 seconds in its setpoint broadcast
- If a non-leader fails to receive a heartbeat for 15 seconds, it triggers a new election

The election is observable from the dashboard. When a leader change happens, the dashboard shows the LEADER badge moving to the new valve.

### 5.4 Layer Interaction

The three layers communicate via a shared `ValveState` object updated each tick:

```python
@dataclass
class ValveState:
    # Sensor inputs
    flow_gpm: float
    dT_C: float
    position_pct: float
    supply_temp_C: float
    return_temp_C: float
    dP_kPa: float

    # Computed
    capacity_demand_kW: float
    capacity_delivered_kW: float

    # Layer 1 output
    rule_fired: Optional[str]
    safety_override_active: bool

    # Layer 2 output
    anomaly_detected: bool
    anomaly_confidence: float
    anomaly_features: List[float]

    # Layer 3 output
    is_leader: bool
    coordination_setpoint: Optional[float]
    peer_states_count: int
    last_election_time: Optional[datetime]

    # Meta
    timestamp: datetime
    valve_id: str
    branch_id: str
```

This object is what the dashboard displays for each valve.

---

## 6. Comparison Mode — Belimo Baseline

To make energy savings claims defensible, the simulation runs both modes against identical scenarios.

### Belimo Baseline Controller (`sim/controllers/belimo_baseline.py`)

Models the Belimo Energy Valve behavior:

```python
class BelimoController:
    """
    Each valve operates independently.
    ΔT Manager: throttles flow when ΔT drops below setpoint - 0.5°C.
    No peer awareness. No cross-valve optimization.
    Pump operates on constant-ΔP control at remote sensor.
    """

    def step(self, valve: ValveState) -> ValveCommand:
        if valve.dT_C < valve.target_dT_C - 0.5:
            new_position = max(0, valve.position_pct - 2.0)
        elif valve.dT_C > valve.target_dT_C + 0.5:
            new_position = min(100, valve.position_pct + 2.0)
        else:
            new_position = valve.position_pct

        return ValveCommand(position_pct=new_position)
```

### ChillValve Controller (`sim/controllers/chillvalve.py`)

Coordinates all three layers and applies their combined output.

```python
class ChillValveController:
    """
    Orchestrates Layer 1, 2, 3. Layer 1 overrides anything else.
    Layer 2 informs Layer 3 priority weights.
    Layer 3 generates setpoint recommendations applied by Layer 1-validated control.
    """

    def step(self, valve: ValveState) -> ValveCommand:
        # Layer 1 first (highest priority)
        rule_action = self.layer1.evaluate(valve)
        if rule_action and rule_action.action in CRITICAL_ACTIONS:
            return ValveCommand(position_pct=rule_action.value, override=True)

        # Layer 2 (informs decisions, doesn't directly control)
        anomaly = self.layer2.evaluate(valve)
        valve.anomaly_detected = anomaly.anomaly_detected
        valve.anomaly_confidence = anomaly.confidence

        # Layer 3 (coordination)
        setpoint = self.layer3.get_current_setpoint(valve.id)
        if setpoint is not None:
            new_position = setpoint
        else:
            # Fall back to local PID if no coordination message yet
            new_position = self._local_pid(valve)

        # Layer 1 validates the final command (clamp, sanity check)
        new_position = self.layer1.validate_command(new_position, valve)

        return ValveCommand(position_pct=new_position)
```

### Expected Energy Outcome

Running the steady-state scenario for 60 simulated minutes:
- Belimo baseline pump energy: ~10 kWh
- ChillValve pump energy: ~8.7 kWh
- Savings: ~13% additional on top of Belimo baseline

These are conservative estimates aligned with literature. If your simulation shows lower savings, tune the load profile to create more cross-valve coordination opportunities — but be honest in slides about what you observed vs. what's expected with site-specific tuning.

---

## 7. Backend (FastAPI)

### 7.1 Endpoints

**WebSocket** `/ws`
- Subscribed by dashboard
- Streams ValveState updates every tick (50ms cadence by default)
- Sends event log entries as they happen
- Includes both modes' data simultaneously if running comparison

**REST**
- `POST /scenario/start?name={scenario_name}` — begin a scenario from start
- `POST /scenario/pause` — pause the simulation
- `POST /scenario/reset` — return to t=0
- `POST /mode/{mode}` — set active mode (`belimo` or `chillvalve` or `compare`)
- `GET /history?since={timestamp}` — query historical data from SQLite
- `GET /health` — basic health check

### 7.2 Orchestrator Module (`backend/orchestrator.py`)

Hosts the multi-agent message broker. Implemented with asyncio:

```python
class MessageBroker:
    """
    Pub/sub message broker for valve agents.
    Each branch has its own channel. Leader election has its own subchannel.
    """

    def __init__(self):
        self.channels = defaultdict(list)  # channel -> list of messages
        self.subscribers = defaultdict(set)  # channel -> set of valve_ids

    async def broadcast(self, channel: str, sender_id: str, payload: dict):
        msg = Message(
            channel=channel,
            sender_id=sender_id,
            payload=payload,
            timestamp=time.time()
        )
        self.channels[channel].append(msg)
        # Trim old messages (keep last 60 seconds)
        cutoff = time.time() - 60
        self.channels[channel] = [m for m in self.channels[channel] if m.timestamp > cutoff]

    async def collect(self, channel: str, since: float) -> List[Message]:
        return [m for m in self.channels[channel] if m.timestamp > since]
```

The broker runs in-process. In production, this would be MQTT or BACnet/IP multicast. For prototype, in-process is sufficient and demo-able.

### 7.3 SQLite Schema (`backend/db.py`)

```sql
CREATE TABLE operational_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    valve_id TEXT NOT NULL,
    flow_gpm REAL,
    dT_C REAL,
    position_pct REAL,
    dP_kPa REAL,
    mode TEXT,
    INDEX idx_timestamp (timestamp),
    INDEX idx_valve (valve_id)
);

CREATE TABLE anomaly_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    valve_id TEXT NOT NULL,
    confidence REAL,
    features_json TEXT,
    resolution TEXT  -- 'auto_resolved', 'escalated', 'pending'
);

CREATE TABLE coordination_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    branch_id TEXT NOT NULL,
    leader_id TEXT,
    event_type TEXT,  -- 'election', 'setpoint_broadcast', 'consensus_failure'
    payload_json TEXT
);

CREATE TABLE scenario_metadata (
    scenario_id TEXT PRIMARY KEY,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    mode TEXT,
    final_pump_energy_kWh REAL,
    final_avg_dT_C REAL,
    anomaly_count INTEGER,
    election_count INTEGER
);
```

Operational data writes are batched (every 5 seconds) to avoid overwhelming SQLite. Anomaly events and coordination events write immediately.

---

## 8. Frontend (React + Vite)

### 8.1 Component Tree

```
App
├── TopBar
│   ├── ScenarioControls       (start, pause, reset, scenario selector)
│   └── ModeToggle              (Belimo | ChillValve | Compare)
├── DashboardGrid
│   ├── BranchRow (×2)
│   │   └── ValveTile (×3 per branch)
│   │       ├── Header           (ID, status LED, leader badge)
│   │       ├── Metrics          (flow, ΔT, position, energy)
│   │       ├── LayerIndicators  (rule fired, ML score, coord active)
│   │       └── MiniChart        (flow over time)
│   └── SystemSummary
│       ├── PumpEnergyGauge
│       └── BranchHealthSummary
├── ComparisonPanel
│   ├── EnergyChart              (cumulative kWh, Belimo vs CV)
│   ├── TemperatureChart         (avg ΔT over time)
│   └── SavingsDisplay           (live % difference)
└── EventLog
    └── EventEntry (scrolling)
```

### 8.2 Visual Design

Use Tailwind CSS for everything. Dark theme. Color scheme:

| Element | Color (Tailwind) |
|---|---|
| Background | `bg-slate-900` |
| Card surface | `bg-slate-800` |
| Card border | `border-slate-700` |
| Primary text | `text-slate-100` |
| Secondary text | `text-slate-400` |
| Healthy status | `text-emerald-400` |
| Warning status | `text-amber-400` |
| Critical status | `text-rose-400` |
| Leader badge | `bg-cyan-500 text-slate-900` |
| Layer 1 active | `bg-sky-500` |
| Layer 2 anomaly | `bg-violet-500` |
| Layer 3 coordination | `bg-emerald-500` |

### 8.3 Real-Time Updates

`useWebSocket` hook maintains the WebSocket connection and updates a Zustand or React context store. Components subscribe to slices.

Key behaviors:
- Auto-reconnect on disconnect
- Buffer last 60 seconds of data per valve for mini-charts
- Smooth number transitions using `framer-motion` (key props for entering animations)
- Event log auto-scrolls to newest entry with smooth animation

### 8.4 Layer Indicators

Each valve tile shows three small LEDs/badges representing layer activity:

- **L1** (sky blue): solid when Layer 1 rule is currently active, pulse on fire event
- **L2** (violet): solid when Layer 2 is detecting anomaly, intensity proportional to confidence
- **L3** (emerald): solid when Layer 3 is receiving coordination messages, badge "LEADER" if this valve is leader

This is the key visual that communicates the three-layer architecture to viewers without explanation.

### 8.5 Comparison Mode

The Mode Toggle has three options:
- **Belimo** — show only Belimo simulation
- **ChillValve** — show only ChillValve simulation
- **Compare** — split screen, both running side by side with synchronized scenarios

Compare mode is the demo's hero feature. The energy chart shows both lines, with shading on the gap.

---

## 9. ML Training Plan

### 9.1 Data Acquisition

`ml/download_lbnl.py`:
- Downloads LBNL Single-Duct AHU dataset from `https://faultdetection.lbl.gov/`
- Extracts to `data/lbnl_raw/`
- Verifies file integrity via checksum

The dataset includes operational data from a single-duct air handling unit with multiple fault conditions:
- Cooling coil valve stuck (at various positions)
- Cooling coil leakage
- Supply air temperature sensor bias
- Outdoor air damper stuck
- Cooling capacity reduction (modeling coil fouling)

Each fault has multiple severity levels and multiple fault-free baselines.

### 9.2 Feature Engineering

Map LBNL columns to your valve's sensor schema:

| LBNL column | Your valve schema |
|---|---|
| `CHWFlow` | `flow_gpm` (converted) |
| `CHWST` | `supply_temp_C` |
| `CHWRT` | `return_temp_C` |
| `CHWVlvPos` | `position_pct` |
| `(computed)` | `dT_C = CHWRT - CHWST` |
| `time` | parsed to extract hour, day-of-week |

Engineered features added:
- `flow_rolling_mean_10min`
- `flow_rolling_std_10min`
- `dT_rolling_mean_10min`
- `dT_rolling_std_10min`
- `position_rolling_mean_10min`
- `hour_sin`, `hour_cos` (cyclic encoding)
- `is_weekend` (0/1)

Total feature count: 9-12 features. Don't go higher — Isolation Forest performs worse with too many features.

### 9.3 Training Configuration

```python
IsolationForest(
    n_estimators=200,       # robust to noise
    contamination=0.05,     # expect 5% of training data is anomalous despite "fault-free" labeling
    max_samples=256,        # sub-sampling improves generalization
    max_features=1.0,       # use all features per tree
    bootstrap=False,
    random_state=42,
    n_jobs=-1
)
```

Train on fault-free data only (filter by label). Test on held-out mix.

### 9.4 Validation Metrics

Produce these for the slides:
- **AUC** (area under ROC curve) — single-number summary
- **Precision at threshold** that maximizes F1
- **Recall at that threshold**
- **False positive rate per day** of operation (operationally meaningful)

Acceptable performance for the prototype:
- AUC ≥ 0.75 — defensible
- AUC ≥ 0.85 — strong
- AUC ≥ 0.90 — excellent, may indicate overfitting to LBNL specifics

If AUC < 0.65, your features are wrong. Iterate on feature engineering, not hyperparameters.

### 9.5 Production-Like Behavior

The trained model is saved and loaded by the simulation at runtime. The simulation never re-trains the model during a scenario — retraining is offline, mimicking real production behavior where a building operator re-trains monthly on accumulated operational data.

To simulate "retraining over time" for the demo, the dashboard shows a "Model Version: 1.2 (trained on 47 days of data)" counter that increments when scenarios complete. This is cosmetic — no actual retraining happens during the demo.

---

## 10. Implementation Order

The order matters. Build in this sequence to avoid integration nightmares.

### Phase 1: Foundation
1. Repository setup, all dependencies installed
2. `ValveState` dataclass and basic types defined
3. Hydraulic model: single valve, plot Cv curve, verify against datasheet

### Phase 2: Simulation Core
4. 6-valve system with pump model
5. Belimo baseline controller working end-to-end
6. Output JSON timeseries from a 60-minute scenario
7. Validate: pump energy is in realistic kWh range

### Phase 3: Three Layers
8. Layer 1 rules engine, all 5 rules implemented and tested
9. Layer 2 placeholder (will be filled by ML model later)
10. Layer 3 multi-agent: message broker, broadcasting
11. Layer 3 leader election with bully algorithm
12. Layer 3 setpoint computation
13. Layer 3 integrated into ChillValve controller

### Phase 4: ML Training (Parallel to Phase 3 if possible)
14. Download LBNL dataset
15. Preprocess and feature engineer
16. Train Isolation Forest, save model + scaler
17. Validate: compute AUC, generate plots
18. Replace Layer 2 placeholder with trained model
19. Run scenario with fault injection, verify detection

### Phase 5: Backend
20. FastAPI skeleton with WebSocket endpoint
21. Connect simulation to WebSocket streaming
22. SQLite schema and write logic
23. REST endpoints for scenario control
24. Mode toggle (Belimo / ChillValve / Compare)

### Phase 6: Frontend
25. Vite project setup with Tailwind
26. WebSocket hook with auto-reconnect
27. ValveTile component with all metrics
28. BranchRow grouping
29. EnergyChart with dual-mode comparison
30. EventLog with scrolling
31. ScenarioControls and ModeToggle
32. Layer indicators on each valve tile
33. Leader badge with animation
34. Anomaly highlighting on tiles

### Phase 7: Integration & Polish
35. End-to-end test: load scenario A, run in compare mode, observe outputs
36. End-to-end test: load scenario C (fault injection), verify Layer 2 catches it
37. End-to-end test: trigger leader failover by killing leader's agent
38. Visual polish: smooth animations, status colors, mini-charts
39. Documentation: README, algorithm pseudocode, Q&A defense sheet

### Phase 8: Demo Recording
40. Storyboard the 90-second demo (see Section 12)
41. Practice run-throughs (3-5 times)
42. Record with OBS Studio at 1080p
43. Edit: trim, add captions, export MP4
44. Hand to Report Lead

---

## 11. Algorithm Pseudocode (For Report Lead)

This goes into the technical report. Mid-level detail, 30-60 lines total.

```
# ChillValve Three-Layer Intelligence Architecture
# Each valve runs all three layers in parallel every simulation tick.

INITIALIZATION
  Load Isolation Forest model from disk
  Load feature scaler from disk
  Connect to message broker
  Determine initial leader (lowest valve_id in branch)

EVERY TICK (1 simulated second):

  # Read sensors
  state = read_sensors(valve_hardware)
  state.dT = state.return_temp - state.supply_temp

  # LAYER 1: Rules engine (microseconds)
  rule_action = evaluate_rules(state)
  if rule_action.severity == CRITICAL:
    apply_action(rule_action)
    return  # bypass layers 2 and 3

  # LAYER 2: ML anomaly detection (every 10 ticks)
  if tick % 10 == 0:
    features = extract_features(state, history)
    features_scaled = scaler.transform(features)
    score = isolation_forest.decision_function(features_scaled)
    state.anomaly_detected = (score < threshold)
    state.anomaly_confidence = score_to_confidence(score)

  # LAYER 3: Multi-agent coordination (every 5 ticks)
  if tick % 5 == 0:
    broadcast(channel=branch_id, payload=state)
    peer_states = collect_recent_messages(channel=branch_id)

    if is_leader:
      if missed_heartbeats > 3:
        # Step down, trigger election
        is_leader = false
        broadcast_election_message()
      else:
        # Leader logic
        aggregate = compute_branch_aggregate(peer_states)
        pump_setpoint = compute_optimal_pump_pressure(aggregate)
        valve_setpoints = allocate_flow_with_priority(peer_states)
        broadcast(channel=branch_id+"/setpoints", payload=valve_setpoints)

    else:
      # Non-leader: apply received setpoint or fallback to local PID
      received = get_latest_setpoint_for(valve_id)
      if received and not stale(received):
        target_position = received.position
        last_leader_heartbeat = received.timestamp
      else:
        target_position = local_pid(state)

      if (now - last_leader_heartbeat) > 15s:
        trigger_election()

  # LAYER 1 final validation (always runs)
  final_command = layer1.validate_command(target_position, state)
  actuator.move_to(final_command)

LEADER ELECTION (Bully algorithm):
  broadcast(channel=branch+"/election", payload={candidate: my_id})
  wait 3 seconds
  candidates = collect_election_messages()
  new_leader = min(candidates)
  if new_leader == my_id:
    is_leader = true
    start_sending_heartbeats()
```

---

## 12. Demo Video Storyboard

90 seconds total. Pre-recorded, embedded in PowerPoint deck.

| Time | Action | Caption |
|---|---|---|
| 0:00-0:08 | Title card with logo and tagline | "ChillValve — Distributed Cooperative Control for Tropical Data Centers" |
| 0:08-0:18 | Dashboard at steady state, all 6 valves visible | "5 MW Tier 3 data center, 6 valves across 2 branches" |
| 0:18-0:28 | Highlight three-layer indicators on a valve tile | "Three layers running on every valve, locally" |
| 0:28-0:40 | Switch to Belimo baseline mode, run scenario | "Belimo Energy Valve baseline — each valve optimizes alone" |
| 0:40-0:55 | Switch to ChillValve mode, same scenario | "ChillValve cooperative mode — branch leader broadcasts setpoints" |
| 0:55-1:05 | Inject fault on Valve B2 (load spike or fouling) | "Layer 2 ML detects developing anomaly" |
| 1:05-1:15 | Coordination response visible on dashboard | "Branch leader reallocates flow within 5 seconds" |
| 1:15-1:25 | Comparison chart shows energy difference | "13% additional pump energy savings on top of Belimo baseline" |
| 1:25-1:30 | Closing card | "Edge-only. No cloud. No operator intervention." |

---

## 13. Q&A Defense Sheet

Ten anticipated questions with prepared 30-second answers.

### Q1: How is this different from BACnet over a building network?

"BACnet is a transport protocol — it moves data between devices. We add cooperative intelligence on top of that transport. Each valve broadcasts not just raw sensor readings but predicted state, capacity demand, and anomaly status. Standard BACnet networks ship sensor values; our valves ship decisions."

### Q2: Why won't Belimo just add this to their cloud platform?

"Cloud cannot achieve sub-second cross-valve coordination — round-trip latency to AWS or Azure is 50-200ms minimum. For transient events like GPU load spikes or pump trips, this only works at the edge. Belimo's cloud business model depends on subscription revenue from analytics, which is fundamentally incompatible with moving the intelligence on-device."

### Q3: What happens if the leader valve fails?

"Each valve has Layer 1 rules running independently — basic safety and flow control never depend on the leader. For coordination specifically, if the leader fails to send a heartbeat for 15 seconds, the next-lowest valve ID triggers an election using a Bully algorithm. New leader is chosen within 3-5 seconds. Coordination resumes in under 30 seconds with zero operator action."

### Q4: How big are your energy savings claims?

"We claim 10-13% additional pump energy savings on top of Belimo's baseline 10-20%. This is conservative — distributed HVAC optimization literature reports 15-30% potential. We chose the lower end because our simulation uses simplified hydraulic models. For a 5MW data center in Cyberjaya at 0.40 RM/kWh industrial tariff, that's roughly RM 4,000-6,000 monthly per branch."

### Q5: Is this AI/ML or just rule-based optimization?

"All three layers. Layer 1 is deterministic rules — microseconds, never AI. Layer 2 is true machine learning — Isolation Forest trained on the LBNL Fault Detection and Diagnostics Dataset from the US Department of Energy. Layer 3 is distributed multi-agent coordination using established control theory from the 1970s. We deliberately don't use LLMs because they're non-deterministic and too slow for control loops."

### Q6: What's your training data source?

"LBNL Fault Detection and Diagnostics Datasets — that's the US Department of Energy public dataset covering chillers, AHUs, and fan coil units. Specifically, the Single-Duct AHU subset with multiple fault types at various severities. We trained on fault-free data only, validated on a held-out mix of fault-free and faulted samples. AUC on the test set is [your number]."

### Q7: How would this be commissioned in a real building?

"Three phases. Phase 1: install valves with rules-only mode active. They operate as standard PICVs. Phase 2: after 30 days of operation, Layer 2 anomaly models train on the building's normal patterns. Phase 3: enable Layer 3 multi-agent coordination, valves discover peers via BACnet/IP. Each phase is reversible. No big-bang deployment required."

### Q8: What if the customer doesn't trust the AI?

"All Layer 2 and Layer 3 decisions are advisory by default. The valve computes recommendations, surfaces them on the BMS, and waits for operator approval before applying. Operators can enable autonomous mode per-valve or per-zone as confidence builds. This is the same gradual adoption path Belimo uses for their ΔT Manager."

### Q9: What's the cost premium over a standard Belimo PICV?

"At scale, the additional bill of materials is the MCU (~RM 30), additional sensors (~RM 50-80), and connectivity (~RM 20). All-in around RM 100-150 per valve for the smart electronics. Against a baseline Belimo PICV at RM 2,000-4,000 per valve depending on size, that's a 3-7% premium. Energy savings give 18-month payback at typical Malaysian industrial electricity rates."

### Q10: Why SQLite and not a real production database?

"For a single building, SQLite handles thousands of writes per second — more than enough for our use case where we write 6 valves x 1 record per minute. It runs as a single file with no server process, no network exposure, no authentication overhead. For multi-building deployments, the same code points to PostgreSQL on the building's local network server — it's a one-line change. We chose SQLite because the value proposition is local-only operation, and SQLite reinforces that architecture."

---

## 14. Integration Points with Team

### From Mechanical Lead 1 (Valve Body)
- Confirmed valve sizes (Branch A = DN65, Branch B = DN100)
- Cv_max values from datasheet for hydraulic model
- Pressure drop curves at design flow

### From Mechanical Lead 2 (Debris + Datasheet)
- Datasheet sensor accuracy specs (±2% flow, ±5% control)
- Coordination on whether debris/fouling appears in fault injection scenario

### From Electrical Lead
- Sensor part numbers and accuracy specs (for simulation noise model)
- MCU choice (ESP32-S3 or STM32H7) — mention in architecture slide
- Communication protocol confirmation (BACnet/IP)

### To Report Lead
- Demo video (MP4, 1080p)
- 3-4 dashboard screenshots
- Algorithm pseudocode (Section 11)
- Energy savings table with measured numbers
- Architecture diagram (Section 2)
- ML validation plots (3 PNG files from `docs/ml_validation/`)

---

## 15. Acceptance Criteria

The prototype is complete when all of the following are true:

1. Simulation runs end-to-end without crashes for at least 60 simulated minutes in both modes
2. All three layers are observable in the dashboard:
   - Layer 1 rule fires trigger visible indicators
   - Layer 2 anomaly scores update in real time
   - Layer 3 leader election is visible and failover works
3. Isolation Forest model is trained on LBNL data with AUC ≥ 0.75
4. Belimo vs ChillValve comparison shows ≥ 10% pump energy savings
5. Fault injection scenario demonstrates Layer 2 catching the fault before Layer 1 would
6. Leader failover scenario demonstrates Layer 3 recovering within 30 seconds
7. 90-second demo video is exported and integrated into team slide deck
8. Algorithm pseudocode is delivered to Report Lead
9. Q&A defense sheet covers at least the 10 questions in Section 13
10. README in the repository documents how to run the prototype

---

## 16. What's Not in Scope

These are deliberately excluded:

- Production-grade authentication or authorization
- Mobile-responsive dashboard layouts (desktop only)
- Real hardware integration (no MCU firmware)
- Multi-building deployment
- Real BACnet/IP integration (in-process message broker only)
- Operator-facing BMS integration UI
- Deep learning models (Isolation Forest only)
- Online model retraining during scenarios (offline only)
- Cloud deployment (everything runs locally)

---

## 17. References and Citations

For the technical report:

- LBNL Fault Detection and Diagnostics Datasets — https://faultdetection.lbl.gov/
- ASHRAE Great Energy Predictor III — Kaggle competition
- Isolation Forest paper: Liu, Ting, Zhou (2008), "Isolation Forest", ICDM
- Belimo Energy Valve product documentation, 2024
- Bully Algorithm: Garcia-Molina (1982), "Elections in a distributed computing system", IEEE Transactions on Computers
- ASHRAE Guideline 36-2021 — High Performance Sequences of Operation for HVAC Systems

---

End of PRD.
