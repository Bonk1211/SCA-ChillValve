import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Landing from "../Landing";
import ClaimCard from "../ClaimCard";

describe("Landing", () => {
  it("renders hero, stack, claim, and CTA", () => {
    render(<Landing onEnter={() => {}} />);
    expect(screen.getByText(/Agentic chilled-water control/i)).toBeInTheDocument();
    expect(screen.getByText("3-LAYER STACK")).toBeInTheDocument();
    expect(screen.getByText("DEFENSIBLE ENERGY CLAIM")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /OPEN THE SIMULATOR/i })).toBeInTheDocument();
  });

  it("invokes onEnter when CTA clicked", () => {
    const onEnter = vi.fn();
    render(<Landing onEnter={onEnter} />);
    fireEvent.click(screen.getByRole("button", { name: /OPEN THE SIMULATOR/i }));
    expect(onEnter).toHaveBeenCalledTimes(1);
  });
});

describe("ClaimCard", () => {
  // Numbers must match the worked-example output of sim/energy_framework.py.
  it("shows worked-example framework figures", () => {
    render(<ClaimCard />);
    expect(screen.getByText("4.71")).toBeInTheDocument();
    expect(screen.getByText("2.7 · 4.7 · 6.8")).toBeInTheDocument();
    expect(screen.getByText("1,954")).toBeInTheDocument();
    expect(screen.getByText("0.79")).toBeInTheDocument();
  });
});
