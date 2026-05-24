import { describe, it, expect } from "vitest";
import { isImpaired } from "../impairment";

describe("isImpaired", () => {
  it("flags low flow on a branch-B valve (45% of 150 design)", () => {
    expect(
      isImpaired({ valve_id: "B2", flow_gpm: 68, anomaly_confidence: 0.1 }),
    ).toBe(true);
  });

  it("flags high anomaly confidence on a branch-A valve at full design flow", () => {
    expect(
      isImpaired({ valve_id: "A2", flow_gpm: 48, anomaly_confidence: 0.5 }),
    ).toBe(true);
  });

  it("flags both triggers together", () => {
    expect(
      isImpaired({ valve_id: "B2", flow_gpm: 30, anomaly_confidence: 0.6 }),
    ).toBe(true);
  });

  it("returns false when flow is at design AND confidence is low", () => {
    expect(
      isImpaired({ valve_id: "A1", flow_gpm: 48, anomaly_confidence: 0.1 }),
    ).toBe(false);
  });

  it("returns false defensively for null input", () => {
    expect(isImpaired(null)).toBe(false);
  });

  it("falls back to 50 GPM design when valve_id is unknown", () => {
    // 10 < 0.6 * 50 = 30 → impaired
    expect(
      isImpaired({ valve_id: "X9", flow_gpm: 10, anomaly_confidence: 0 }),
    ).toBe(true);
  });
});
