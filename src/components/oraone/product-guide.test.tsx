import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProductGuide } from "./product-guide";

describe("ProductGuide", () => {
  it("renders the what-it-does text and the needs list under plain headings", () => {
    render(
      <ProductGuide
        whatItDoes="Shows conversations with customers."
        needs={["A connected channel.", "A chat widget on your site."]}
      />,
    );

    const region = screen.getByRole("region", { name: "About this screen" });
    expect(within(region).getByRole("heading", { level: 2, name: "What this does" })).toBeTruthy();
    expect(within(region).getByText("Shows conversations with customers.")).toBeTruthy();
    expect(
      within(region).getByRole("heading", { level: 2, name: "What you need before it works" }),
    ).toBeTruthy();

    const items = within(region).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "A connected channel.",
      "A chat widget on your site.",
    ]);
  });

  it("renders terms as a labelled definition list when provided", () => {
    render(
      <ProductGuide
        whatItDoes="Shows statuses."
        needs={["Nothing to set up."]}
        terms={[{ term: "Connected", meaning: "Linked to your workspace." }]}
        termsHeading="Status meanings"
      />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "Status meanings" })).toBeTruthy();
    expect(screen.getByText("Connected").tagName).toBe("DT");
    expect(screen.getByText("Linked to your workspace.").tagName).toBe("DD");
  });

  it("omits the terms block when no terms are given", () => {
    render(<ProductGuide whatItDoes="Shows billing." needs={["Nothing to set up."]} />);

    expect(screen.queryByRole("heading", { name: "Key terms" })).toBeNull();
    expect(screen.queryByRole("definition")).toBeNull();
  });
});
