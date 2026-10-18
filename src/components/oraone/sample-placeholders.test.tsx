import { render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspacePage } from "./pages";

// These pages only need the router to read the current path and to render links; a
// full router is not required to check the sample values.
vi.mock("@tanstack/react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-router")>();
  return {
    ...actual,
    useRouterState: () => "/app",
    Link: ({ to, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { to?: string }) => (
      <a href={to} {...rest} />
    ),
  };
});

describe("sample workspace placeholders", () => {
  it("shows no made-up satisfaction score on the analytics page", () => {
    render(<WorkspacePage title="Analytics" pagePath="/app/products/chat/analytics" />);

    expect(document.body.textContent).not.toContain("4.8/5");
    expect(screen.getByText("Not connected yet")).toBeTruthy();
  });

  it("leaves the account email empty and shows only a placeholder", () => {
    render(<WorkspacePage title="Account" pagePath="/app/account" />);

    const email = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    expect(email).not.toBeNull();
    expect(email?.value).toBe("");
    expect(email?.placeholder).toBe("Your email address");
    expect(document.body.textContent).not.toContain("alex@example.com");
  });

  it("leaves the workspace website empty and shows only a placeholder", () => {
    render(<WorkspacePage title="Settings" pagePath="/app/settings" />);

    const website = document.querySelector('input[type="url"]') as HTMLInputElement | null;
    expect(website).not.toBeNull();
    expect(website?.value).toBe("");
    expect(website?.placeholder).toBe("Your website address");
    expect(document.body.innerHTML).not.toContain("https://example.com");
  });
});
