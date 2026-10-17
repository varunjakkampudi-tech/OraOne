// Shared layout tokens for the public site. Every section, the header and the footer use
// CONTAINER, so content lines up with the logo on every page.

/** One content width and gutter: 16px mobile, 24px tablet, 32px desktop. */
export const CONTAINER = "mx-auto w-full max-w-[1200px] px-4 sm:px-6 lg:px-8";

/** Vertical rhythm between sections. Never more than 64px on desktop. */
export const SECTION_Y = "py-10 md:py-16";

/**
 * The primary action goes to the demo workspace, which exists today. Sign-up and trials
 * are not promised, because live sign-in and service connections are still being verified.
 */
export const PRIMARY_CTA = { label: "Explore the demo", to: "/app" } as const;
export const SECONDARY_CTA = { label: "Sign in", to: "/auth/sign-in" } as const;
