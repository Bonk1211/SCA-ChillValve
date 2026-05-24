import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ValveTile from "../ValveTile";

const baseValve = {
  valve_id: "A1",
  branch_id: "A",
  flow_gpm: 21.5,
  dT_C: 5.0,
  position_pct: 50,
  is_leader: false,
  anomaly_detected: false,
  anomaly_confidence: 0,
  rule_fired: null,
  safety_override_active: false,
};

describe("ValveTile", () => {
  it("renders valve id and metrics", () => {
    render(<ValveTile valve={baseValve} />);
    expect(screen.getByText("A1")).toBeInTheDocument();
    expect(screen.getByText("22")).toBeInTheDocument(); // 21.5 rounded
    expect(screen.getByText("5.0")).toBeInTheDocument();
  });

  it("shows LEADER badge when is_leader=true", () => {
    render(<ValveTile valve={{ ...baseValve, is_leader: true }} />);
    expect(screen.getByText("LEADER")).toBeInTheDocument();
  });

  it("hides LEADER badge when is_leader=false", () => {
    render(<ValveTile valve={baseValve} />);
    expect(screen.queryByText("LEADER")).not.toBeInTheDocument();
  });

  it("renders all three layer indicator labels", () => {
    render(<ValveTile valve={baseValve} />);
    expect(screen.getByText("L1")).toBeInTheDocument();
    expect(screen.getByText("L2")).toBeInTheDocument();
    expect(screen.getByText("L3")).toBeInTheDocument();
  });
});
