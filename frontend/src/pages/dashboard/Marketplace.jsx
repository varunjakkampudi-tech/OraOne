import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Store,
  Search,
  Check,
  Loader2,
  Sparkles,
  Trash2,
  ArrowRight,
} from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  Segmented,
  PrimaryButton,
  GhostButton,
  EmptyState,
  SUB,
  INK,
  LINE,
} from "@/components/dashboard/kit";
import { marketplaceApi } from "@/lib/marketplace";
import { formatApiError } from "@/lib/api";
import { Stars, ReviewsModal } from "@/pages/dashboard/MarketplaceReviews";

const ALL = { value: "all", label: "All" };

export default function Marketplace() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([ALL]);
  const [active, setActive] = useState("all");
  const [query, setQuery] = useState("");
  const [listings, setListings] = useState([]);
  const [installs, setInstalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null); // slug or installation id being mutated
  const [error, setError] = useState("");
  const [reviewing, setReviewing] = useState(null); // listing whose reviews are open

  const installedSlugs = useMemo(
    () => new Set(installs.map((i) => i.listing_slug)),
    [installs]
  );

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [cats, items, mine] = await Promise.all([
        marketplaceApi.categories(),
        marketplaceApi.listings({
          category: active === "all" ? undefined : active,
          q: query.trim() || undefined,
        }),
        marketplaceApi.installations(),
      ]);
      setCategories([ALL, ...cats]);
      setListings(items);
      setInstalls(mine);
    } catch (e) {
      setError(formatApiError(e?.response?.data?.detail) || "Failed to load marketplace.");
    } finally {
      setLoading(false);
    }
  }

  // Re-fetch listings when filter/search changes (categories + installs come along).
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  async function onSearch(e) {
    e.preventDefault();
    refresh();
  }

  async function install(listing) {
    setBusy(listing.slug);
    setError("");
    try {
      const res = await marketplaceApi.install(listing.slug);
      await refresh();
      // For agent templates, jump straight into the new agent.
      if (res?.agent_id) navigate(`/app/agents/${res.agent_id}`);
    } catch (e) {
      setError(formatApiError(e?.response?.data?.detail) || "Install failed.");
    } finally {
      setBusy(null);
    }
  }

  async function uninstall(inst) {
    setBusy(inst.id);
    setError("");
    try {
      await marketplaceApi.uninstall(inst.id);
      await refresh();
    } catch (e) {
      setError(formatApiError(e?.response?.data?.detail) || "Uninstall failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Store}
        eyebrow="Marketplace"
        title="AI Marketplace"
        subtitle="Install ready-made agents, integrations and workflows in one click."
      />

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Segmented
          value={active}
          onChange={setActive}
          options={categories.map((c) => ({ value: c.value, label: c.label }))}
        />
        <form onSubmit={onSearch} className="relative w-full sm:w-72">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2"
            style={{ color: SUB }}
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the catalogue…"
            className="w-full rounded-lg border bg-white py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-[#2563EB]/20"
            style={{ borderColor: LINE, color: INK }}
          />
        </form>
      </div>

      {/* Installed strip */}
      {installs.length > 0 ? (
        <Card className="p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold" style={{ color: INK }}>
            <Check className="h-4 w-4 text-emerald-600" />
            Installed ({installs.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {installs.map((inst) => (
              <span
                key={inst.id}
                className="group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm"
                style={{ borderColor: LINE, color: INK }}
              >
                {inst.listing_name}
                <button
                  type="button"
                  onClick={() => uninstall(inst)}
                  disabled={busy === inst.id}
                  className="text-slate-400 hover:text-red-600 disabled:opacity-50"
                  aria-label={`Uninstall ${inst.listing_name}`}
                >
                  {busy === inst.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" />
                  )}
                </button>
              </span>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Catalogue grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20" style={{ color: SUB }}>
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading marketplace…
        </div>
      ) : listings.length === 0 ? (
        <EmptyState
          icon={Store}
          title="No listings found"
          hint="Try a different category or search term."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {listings.map((l) => {
            const isInstalled = installedSlugs.has(l.slug);
            return (
              <Card key={l.slug} hover className="flex flex-col p-5">
                <div className="flex items-start justify-between">
                  <div
                    className="flex h-11 w-11 items-center justify-center rounded-xl text-2xl"
                    style={{ background: "#EFF4FF" }}
                  >
                    {l.icon}
                  </div>
                  {l.featured ? (
                    <Badge tone="indigo">
                      <Sparkles className="mr-1 inline h-3 w-3" /> Featured
                    </Badge>
                  ) : null}
                </div>
                <h3 className="mt-3 text-base font-semibold" style={{ color: INK }}>
                  {l.name}
                </h3>
                <p className="mt-1 flex-1 text-sm leading-relaxed" style={{ color: SUB }}>
                  {l.summary}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {l.tags.slice(0, 3).map((t) => (
                    <Badge key={t} tone="slate">
                      {t}
                    </Badge>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setReviewing(l)}
                  className="mt-3 inline-flex w-fit items-center gap-1 rounded-md px-1 py-0.5 hover:bg-slate-50"
                  aria-label={`Reviews for ${l.name}`}
                >
                  <Stars value={l.rating || 0} count={l.review_count ?? 0} />
                </button>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-xs" style={{ color: SUB }}>
                    by {l.author}
                  </span>
                  {isInstalled ? (
                    <GhostButton disabled>
                      <Check className="mr-1.5 h-4 w-4 text-emerald-600" /> Installed
                    </GhostButton>
                  ) : (
                    <PrimaryButton onClick={() => install(l)} disabled={busy === l.slug}>
                      {busy === l.slug ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : (
                        <ArrowRight className="mr-1.5 h-4 w-4" />
                      )}
                      Install
                    </PrimaryButton>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {reviewing && (
        <ReviewsModal
          listing={reviewing}
          onClose={() => setReviewing(null)}
          onChanged={refresh}
        />
      )}
    </div>
  );
}
