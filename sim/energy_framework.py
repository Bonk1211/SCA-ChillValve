"""Energy-savings framework. Implements the Step 1–6 calculation from
the project brief.

Inputs are split into MEASURED (from this scenario run) and ASSUMED (fault
catalog, drift, overheads). Outputs include low/mid/high sensitivity bands
and a confidence-weighted net result, so a reviewer can see what is
empirical vs what is parameterized.

NOTE on claims this module is careful NOT to make:
  - "Earlier detection" is reported as a time-delta in seconds, derived from
    the AI's actual anomaly-onset-to-detection window in the measured run
    and a Belimo-equivalent reactive-threshold counterfactual. No hand-wave.
  - Self-calibration credit is multiplied by a confidence factor: if mean
    anomaly_confidence in the run is low (drifting reference / noisy ML),
    the credit shrinks. Never assumes the AI is right.
  - False-positive cost is subtracted from gross savings, not ignored.

Wire-up: backend.orchestrator._emit_summary calls compute(MeasuredRun(...))
and folds the result dict into the WS `summary` message read by
frontend/src/components/v5/SummaryBanner.jsx. No file I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ---------- Step 2: Fault catalog ----------------------------------------
# Default annual occurrence rates and power penalties per fault type, sourced
# from the project brief's worked example. Each row carries a sensitivity
# band so the report can show low/mid/high instead of a point estimate.

@dataclass
class FaultRow:
    name: str
    belimo_detect_s: float      # reactive-threshold typical latency (s)
    ai_detect_s: float          # predictive/signature typical latency (s)
    power_penalty_kw: float     # average pump+chiller overdraw while undetected (kW)
    events_per_year: float
    band_factors: tuple = (0.5, 1.0, 1.5)  # low/mid/high multiplier on events_per_year


DEFAULT_CATALOG: List[FaultRow] = [
    FaultRow("low_dT",         belimo_detect_s=600,      ai_detect_s=120,    power_penalty_kw=5.0,  events_per_year=40),
    FaultRow("stuck_actuator", belimo_detect_s=900,      ai_detect_s=180,    power_penalty_kw=20.0, events_per_year=2),
    FaultRow("valve_hunting",  belimo_detect_s=1800,     ai_detect_s=30,     power_penalty_kw=1.0,  events_per_year=30),
    FaultRow("coil_fouling",   belimo_detect_s=7776000,  ai_detect_s=1814400,power_penalty_kw=1.2,  events_per_year=1),
    FaultRow("air_binding",    belimo_detect_s=14400,    ai_detect_s=300,    power_penalty_kw=8.0,  events_per_year=4),
]


@dataclass
class DriftParams:
    """Step 4: RTD drift / self-cal. Defaults are mid-band from brief."""
    drift_rate_C_per_year: float = 0.2   # typical RTD drift 0.1–0.3 °C/yr
    recal_interval_years: float = 1.0
    design_dT_C: float = 6.0
    base_confidence: float = 0.6         # knocked down further by run confidence


@dataclass
class Overheads:
    """Step 5: subtract these from gross. False-positive penalty is real."""
    edge_compute_w: float = 10.0         # 5–15 W continuous per node
    nodes: int = 5
    false_positive_events_per_year: float = 3.0
    false_positive_penalty_kwh: float = 0.2


@dataclass
class MeasuredRun:
    """What the orchestrator hands the calculator at end-of-run."""
    duration_s: int
    mean_kw_pre_fault: float
    mean_kw_during_fault: float
    mean_kw_post_recovery: float
    recovery_fired: bool
    measured_fault_type: Optional[str]
    ai_detect_latency_s: Optional[float]
    belimo_counterfactual_latency_s: Optional[float]
    mean_anomaly_confidence: float = 0.7
    annual_operating_hours: float = 2500.0


@dataclass
class FaultLine:
    name: str
    e_saved_kwh: float
    detect_advantage_s: float
    power_penalty_kw: float
    events_per_year: float
    measured: bool   # True if this row used measured latency (not catalog)


@dataclass
class FrameworkResult:
    baseline_kwh_annual: float
    per_fault: List[FaultLine] = field(default_factory=list)
    fault_savings_kwh: float = 0.0
    drift_avoided_kwh: float = 0.0
    drift_confidence: float = 0.0
    overhead_edge_kwh: float = 0.0
    overhead_false_positive_kwh: float = 0.0
    overhead_kwh: float = 0.0
    gross_savings_kwh: float = 0.0
    net_savings_kwh: float = 0.0
    net_pct_vs_baseline: float = 0.0
    confidence_weight: float = 0.0
    confidence_weighted_kwh: float = 0.0
    band_low_pct: float = 0.0
    band_mid_pct: float = 0.0
    band_high_pct: float = 0.0
    # Honest-engineering split: coil_fouling row uses a 69-day catalog
    # detection advantage that no reasonable demo run can validate. Headline
    # numbers exclude it; the fouling kWh is exposed separately so the UI can
    # gate it behind an explicit "unvalidated" badge.
    coil_fouling_kwh: float = 0.0
    fault_savings_excl_fouling_kwh: float = 0.0
    gross_savings_excl_fouling_kwh: float = 0.0
    net_savings_excl_fouling_kwh: float = 0.0
    net_pct_excl_fouling: float = 0.0
    confidence_weighted_excl_fouling_kwh: float = 0.0
    band_low_pct_excl_fouling: float = 0.0
    band_mid_pct_excl_fouling: float = 0.0
    band_high_pct_excl_fouling: float = 0.0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["per_fault"] = [asdict(f) for f in self.per_fault]
        return d


def _baseline_kwh(m: MeasuredRun) -> float:
    """Step 1: annualize pre-fault mean pump_kW × operating hours. Pump
    only — sim has no chiller model, don't claim what we don't measure."""
    return m.mean_kw_pre_fault * m.annual_operating_hours


def _fault_savings(catalog: List[FaultRow], m: MeasuredRun) -> List[FaultLine]:
    """Step 3: E_saved_i = N_events × Δt_detect × P_penalty. Substitute
    measured latency + measured penalty for the fault that fired this run."""
    measured_kw_penalty: Optional[float] = None
    if m.mean_kw_during_fault > 0 and m.mean_kw_post_recovery > 0:
        measured_kw_penalty = max(0.0, m.mean_kw_during_fault - m.mean_kw_post_recovery)

    lines: List[FaultLine] = []
    for row in catalog:
        is_match = (
            m.measured_fault_type == row.name
            and m.ai_detect_latency_s is not None
            and m.belimo_counterfactual_latency_s is not None
        )
        if is_match:
            adv_s = max(
                0.0,
                float(m.belimo_counterfactual_latency_s) - float(m.ai_detect_latency_s),
            )
            p_kw = measured_kw_penalty if measured_kw_penalty is not None else row.power_penalty_kw
        else:
            adv_s = max(0.0, row.belimo_detect_s - row.ai_detect_s)
            p_kw = row.power_penalty_kw
        e_kwh = row.events_per_year * (adv_s / 3600.0) * p_kw
        lines.append(FaultLine(
            name=row.name,
            e_saved_kwh=e_kwh,
            detect_advantage_s=adv_s,
            power_penalty_kw=p_kw,
            events_per_year=row.events_per_year,
            measured=is_match,
        ))
    return lines


def _drift_avoided(d: DriftParams, baseline_kwh: float, mean_conf: float) -> tuple:
    """Step 4: cumulative drift-energy penalty avoided over the recal
    interval. Multiplied by base_confidence × mean run anomaly_confidence
    so a low-confidence run does not over-claim self-cal credit."""
    fraction = (d.drift_rate_C_per_year * d.recal_interval_years ** 2) / (2.0 * d.design_dT_C)
    confidence = d.base_confidence * max(0.0, min(1.0, mean_conf))
    return fraction * baseline_kwh * confidence, confidence


def _overheads(o: Overheads, annual_hours: float) -> tuple:
    edge_kwh = (o.edge_compute_w / 1000.0) * annual_hours * o.nodes
    fp_kwh = o.false_positive_events_per_year * o.false_positive_penalty_kwh
    return edge_kwh, fp_kwh


def compute(
    measured: MeasuredRun,
    catalog: Optional[List[FaultRow]] = None,
    drift: Optional[DriftParams] = None,
    overheads_p: Optional[Overheads] = None,
) -> FrameworkResult:
    catalog = catalog or DEFAULT_CATALOG
    drift = drift or DriftParams()
    overheads_p = overheads_p or Overheads()

    res = FrameworkResult(baseline_kwh_annual=_baseline_kwh(measured))
    res.per_fault = _fault_savings(catalog, measured)
    res.fault_savings_kwh = sum(f.e_saved_kwh for f in res.per_fault)

    drift_kwh, drift_conf = _drift_avoided(
        drift, res.baseline_kwh_annual, measured.mean_anomaly_confidence
    )
    res.drift_avoided_kwh = drift_kwh
    res.drift_confidence = drift_conf

    edge_kwh, fp_kwh = _overheads(overheads_p, measured.annual_operating_hours)
    res.overhead_edge_kwh = edge_kwh
    res.overhead_false_positive_kwh = fp_kwh
    res.overhead_kwh = edge_kwh + fp_kwh

    res.gross_savings_kwh = res.fault_savings_kwh + res.drift_avoided_kwh
    res.net_savings_kwh = res.gross_savings_kwh - res.overhead_kwh
    res.net_pct_vs_baseline = (
        100.0 * res.net_savings_kwh / res.baseline_kwh_annual
        if res.baseline_kwh_annual > 0 else 0.0
    )

    # Confidence weighting — never assume AI is right. Mid FP-rate 7.5%.
    fp_rate_assumed = 0.075
    res.confidence_weight = (
        max(0.0, min(1.0, measured.mean_anomaly_confidence)) * (1.0 - fp_rate_assumed)
    )
    res.confidence_weighted_kwh = res.net_savings_kwh * res.confidence_weight

    # Sensitivity bands: scale each fault line's events_per_year by its band factor.
    def _band_pct(idx: int, exclude_fouling: bool = False) -> float:
        fault = sum(
            line.e_saved_kwh * row.band_factors[idx]
            for row, line in zip(catalog, res.per_fault)
            if not (exclude_fouling and line.name == "coil_fouling")
        )
        gross = fault + res.drift_avoided_kwh
        net = gross - res.overhead_kwh
        return (100.0 * net / res.baseline_kwh_annual
                if res.baseline_kwh_annual > 0 else 0.0)

    res.band_low_pct = _band_pct(0)
    res.band_mid_pct = _band_pct(1)
    res.band_high_pct = _band_pct(2)

    # ---- Split fouling out for the defensible headline -------------------
    fouling_line = next(
        (f for f in res.per_fault if f.name == "coil_fouling"), None
    )
    res.coil_fouling_kwh = fouling_line.e_saved_kwh if fouling_line else 0.0
    res.fault_savings_excl_fouling_kwh = (
        res.fault_savings_kwh - res.coil_fouling_kwh
    )
    res.gross_savings_excl_fouling_kwh = (
        res.fault_savings_excl_fouling_kwh + res.drift_avoided_kwh
    )
    res.net_savings_excl_fouling_kwh = (
        res.gross_savings_excl_fouling_kwh - res.overhead_kwh
    )
    res.net_pct_excl_fouling = (
        100.0 * res.net_savings_excl_fouling_kwh / res.baseline_kwh_annual
        if res.baseline_kwh_annual > 0 else 0.0
    )
    res.confidence_weighted_excl_fouling_kwh = (
        res.net_savings_excl_fouling_kwh * res.confidence_weight
    )
    res.band_low_pct_excl_fouling = _band_pct(0, exclude_fouling=True)
    res.band_mid_pct_excl_fouling = _band_pct(1, exclude_fouling=True)
    res.band_high_pct_excl_fouling = _band_pct(2, exclude_fouling=True)
    return res
