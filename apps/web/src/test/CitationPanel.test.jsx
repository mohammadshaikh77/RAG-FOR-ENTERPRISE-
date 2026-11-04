import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CitationPanel } from "../components/chat/CitationPanel.jsx";

describe("CitationPanel Component", () => {
  const sampleCitation = {
    document_title: "Lisinopril Tablets FDA Insert",
    section_title: "Boxed Warning",
    quoted_span: "can cause injury and even death to the developing fetus",
    full_chunk_text:
      "When used in pregnancy during the second and third trimesters, ACE inhibitors can cause injury and even death to the developing fetus. Discontinue as soon as possible.",
    is_verified: true,
  };

  it("renders document title and section name", () => {
    render(
      <CitationPanel
        citation={sampleCitation}
        citationIndex={1}
        onClose={() => {}}
      />
    );

    expect(screen.getByText("Lisinopril Tablets FDA Insert")).toBeInTheDocument();
    expect(screen.getByText("Boxed Warning")).toBeInTheDocument();
    expect(screen.getByText("Grounded Citation")).toBeInTheDocument();
  });

  it("highlights the quoted span within the full chunk text", () => {
    const { container } = render(
      <CitationPanel
        citation={sampleCitation}
        citationIndex={1}
        onClose={() => {}}
      />
    );

    const mark = container.querySelector("mark");
    expect(mark).toBeInTheDocument();
    expect(mark?.textContent).toContain(
      "can cause injury and even death to the developing fetus"
    );
  });
});

