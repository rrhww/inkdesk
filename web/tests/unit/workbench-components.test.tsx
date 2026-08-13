import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WikiCard } from "@/components/workbench/wiki-card";
import { researchTopicSummariesFixture } from "@/lib/mock/research-fixtures";

describe("read-only workbench cards", () => {
  it("renders a wiki node without edit or submit controls", () => {
    render(<WikiCard topic={researchTopicSummariesFixture[0]} />);

    expect(screen.getByRole("link", { name: researchTopicSummariesFixture[0].title })).toHaveAttribute(
      "href",
      `/app/wiki/${researchTopicSummariesFixture[0].id}`,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
