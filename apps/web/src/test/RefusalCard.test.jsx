import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RefusalCard } from "../components/chat/RefusalCard.jsx";

describe("RefusalCard Component", () => {
  it("renders distinct calm card when evidence is not found", () => {
    render(
      <RefusalCard
        message="I cannot answer this question based on the provided documents as no relevant clinical evidence was found."
        query="fake drug test"
      />
    );

    expect(screen.getByText("Not found in your documents")).toBeInTheDocument();
    expect(
      screen.getByText("Strict Hallucination Guardrail Active")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/I cannot answer this question based on the provided documents/)
    ).toBeInTheDocument();
  });
});

