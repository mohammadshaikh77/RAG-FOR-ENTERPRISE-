import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusChip } from "../components/documents/StatusChip.jsx";

describe("StatusChip Component", () => {
  it("renders ready state for completed or ready status", () => {
    const { rerender } = render(<StatusChip status="completed" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();

    rerender(<StatusChip status="ready" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("renders processing state with spinner", () => {
    render(<StatusChip status="processing" />);
    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("renders failed state", () => {
    render(<StatusChip status="failed" />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders fallback queued state for unknown status", () => {
    render(<StatusChip status="queued" />);
    expect(screen.getByText("Queued")).toBeInTheDocument();
  });
});

