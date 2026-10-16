## App architecture

- Keep product availability in a central registry so navigation and page states agree.
- Use shared page-family views with individual TanStack file routes and leaf metadata so every destination supports direct navigation.
- Keep the current experience explicitly demonstrational until identity and service connections are configured; never simulate backend success.
- Mount the workspace shell in the root route around workspace outlets so workspace selection survives client navigation.
- Keep workspace context values referentially stable and preload links on intent so shell controls do not redraw page consumers and destinations warm before navigation.
- Load the isolated dashboard chart lazily and debounce resize measurement so chart dependencies do not block unrelated screens or redraw on every sidebar animation frame.
- Keep marketing, authentication, onboarding and administration in separate page-family modules; the public root and workspace /app stay distinct so dashboard behavior is preserved.
- Use router pending boundaries and Suspense fallbacks for real loading; never introduce artificial service delays or optimistic success for disconnected services.
- Keep preview service capabilities explicit in a shared registry; identity and privileged operations remain unavailable until the authoritative services verify them.
- Load shared readability refinements after the legacy theme stylesheet so all page families retain consistent typography without duplicating page implementations.
- Generate per-leaf canonical and indexing metadata from the route inventory; exclude private previews and unapproved policies from the public sitemap.
- Keep app-tour media opt-in with native video controls and no preload so marketing media does not slow initial navigation.
- Use dialog primitives for mobile navigation so focus, Escape dismissal and scroll locking are shared across all page families.

- Keep recovery aliases as router redirects to one canonical destination so duplicate account screens cannot diverge.
- Derive sidebar selection with exact home matching and explicit route metadata so router prefix matches cannot select two destinations.
- Real signed-in features live under src/routes/_authenticated/ (/studio); /app stays the sample workspace — keeps the demo intact while live data is RLS-scoped by workspace membership.
- Auth is passwordless email code only; password recovery routes redirect to sign-in — there is no password to reset.
- Share one dropdown selection per shell and derive sample details from visible records so menus and filtered details cannot diverge.
