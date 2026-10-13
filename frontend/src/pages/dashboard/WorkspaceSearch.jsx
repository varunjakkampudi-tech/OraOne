import { useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { NAV_GROUPS } from "@/constants/navigation";

const SEARCHABLE_PAGES = NAV_GROUPS.flatMap((group) => group.items)
  .filter((item) => !item.disabled)
  .map(({ label, to, icon: Icon }) => ({ label, to, Icon }));

export default function WorkspaceSearch() {
  const [query, setQuery] = useState("");
  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return SEARCHABLE_PAGES;
    return SEARCHABLE_PAGES.filter((page) =>
      page.label.toLowerCase().includes(normalized),
    );
  }, [query]);

  return (
    <main
      className="mx-auto w-full max-w-4xl space-y-6"
      data-testid="workspace-search-page"
    >
      <header>
        <p className="text-sm font-semibold text-blue-700">Workspace</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
          Find a page
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Search OraOne workspace navigation. This search does not search
          customer records or connected services.
        </p>
      </header>

      <label className="flex min-h-12 items-center gap-3 rounded-xl border border-slate-300 bg-white px-4 focus-within:border-blue-600 focus-within:ring-2 focus-within:ring-blue-100">
        <Search
          size={18}
          className="shrink-0 text-slate-500"
          aria-hidden="true"
        />
        <span className="sr-only">Search workspace pages</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search pages…"
          className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
          data-testid="workspace-search-input"
        />
      </label>

      <section
        aria-live="polite"
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white"
      >
        <h2 className="border-b border-slate-100 px-5 py-3 text-xs font-semibold text-slate-500">
          {results.length
            ? `${results.length} workspace pages`
            : "No pages found"}
        </h2>
        {results.length ? (
          <ul className="divide-y divide-slate-100">
            {results.map(({ label, to, Icon }) => (
              <li key={to}>
                <Link
                  to={to}
                  className="flex min-h-12 items-center gap-3 px-5 py-3 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-blue-700"
                >
                  <Icon
                    size={17}
                    className="text-slate-500"
                    aria-hidden="true"
                  />
                  <span className="flex-1 font-medium">{label}</span>
                  <ArrowRight
                    size={15}
                    className="text-slate-400"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-5 py-6 text-sm text-slate-600">
            Try a shorter page name, such as “agents” or “settings.”
          </p>
        )}
      </section>
    </main>
  );
}
