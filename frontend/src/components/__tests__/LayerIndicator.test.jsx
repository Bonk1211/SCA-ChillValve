import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LayerIndicator from "../LayerIndicator";

describe("LayerIndicator", () => {
  it("renders the layer label", () => {
    render(<LayerIndicator layer="L1" active={false} label="rules" />);
    expect(screen.getByText("L1")).toBeInTheDocument();
  });

  it("uses higher opacity when active", () => {
    render(<LayerIndicator layer="L2" active={true} intensity={0.9} label="" />);
    const dot = screen.getByTestId("indicator-L2");
    expect(parseFloat(dot.style.opacity)).toBeGreaterThanOrEqual(0.4);
  });

  it("uses low opacity when inactive", () => {
    render(<LayerIndicator layer="L3" active={false} label="" />);
    const dot = screen.getByTestId("indicator-L3");
    expect(parseFloat(dot.style.opacity)).toBeLessThan(0.2);
  });
});
