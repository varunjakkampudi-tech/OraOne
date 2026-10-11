import React, { useEffect, useState } from "react";
import { Star, Loader2, X, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PrimaryButton, GhostButton, INK, SUB, LINE } from "@/components/dashboard/kit";
import { marketplaceApi } from "@/lib/marketplace";
import { formatApiError } from "@/lib/api";

// Compact, read-only star rating for listing cards.
export function Stars({ value = 0, size = 14, count }) {
  const full = Math.round(value);
  return (
    <span className="inline-flex items-center gap-1" title={`${value} out of 5`}>
      <span className="inline-flex">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star
            key={i}
            size={size}
            className={i <= full ? "fill-amber-400 text-amber-400" : "text-slate-300"}
          />
        ))}
      </span>
      {count != null && (
        <span className="text-xs" style={{ color: SUB }}>
          {value > 0 ? value.toFixed(1) : "New"}{count > 0 ? ` (${count})` : ""}
        </span>
      )}
    </span>
  );
}

// Interactive star picker for the review form.
function StarPicker({ value, onChange }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(i)}
          aria-label={`${i} star`}
        >
          <Star
            size={26}
            className={i <= (hover || value) ? "fill-amber-400 text-amber-400" : "text-slate-300"}
          />
        </button>
      ))}
    </div>
  );
}

export function ReviewsModal({ listing, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    marketplaceApi
      .reviews(listing.slug)
      .then((d) => {
        setData(d);
        if (d.my_review) {
          setRating(d.my_review.rating);
          setTitle(d.my_review.title || "");
          setBody(d.my_review.body || "");
        }
      })
      .catch((e) => toast.error(formatApiError(e?.response?.data?.detail) || "Failed to load reviews"))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [listing.slug]);

  const submit = () => {
    setSaving(true);
    marketplaceApi
      .submitReview(listing.slug, { rating, title: title.trim() || undefined, body: body.trim() || undefined })
      .then(() => { toast.success("Review saved"); load(); onChanged?.(); })
      .catch((e) => toast.error(formatApiError(e?.response?.data?.detail) || "Could not save review"))
      .finally(() => setSaving(false));
  };

  const removeReview = () => {
    marketplaceApi
      .deleteReview(listing.slug)
      .then(() => { toast.success("Review removed"); setTitle(""); setBody(""); setRating(5); load(); onChanged?.(); })
      .catch((e) => toast.error(formatApiError(e?.response?.data?.detail) || "Could not remove review"));
  };

  const dist = data?.distribution || {};
  const total = data?.count || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b p-5" style={{ borderColor: LINE }}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{listing.icon}</span>
            <div>
              <h3 className="font-semibold" style={{ color: INK }}>{listing.name}</h3>
              <p className="text-xs" style={{ color: SUB }}>Ratings & reviews</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        {loading ? (
          <div className="grid place-items-center py-16" style={{ color: SUB }}><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : (
          <div className="space-y-6 p-5">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-4xl font-bold" style={{ color: INK }}>{(data?.average || 0).toFixed(1)}</div>
                <Stars value={data?.average || 0} size={16} />
                <div className="mt-1 text-xs" style={{ color: SUB }}>{total} review{total === 1 ? "" : "s"}</div>
              </div>
              <div className="flex-1 space-y-1">
                {[5, 4, 3, 2, 1].map((n) => {
                  const c = dist[n] || 0;
                  const pct = total ? (c / total) * 100 : 0;
                  return (
                    <div key={n} className="flex items-center gap-2 text-xs" style={{ color: SUB }}>
                      <span className="w-3">{n}</span>
                      <Star size={11} className="fill-amber-400 text-amber-400" />
                      <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: LINE }}>
                        <div className="h-full rounded-full bg-amber-400" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="w-6 text-right">{c}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border p-4" style={{ borderColor: LINE }}>
              <p className="text-sm font-semibold" style={{ color: INK }}>
                {data?.my_review ? "Edit your review" : "Write a review"}
              </p>
              <div className="mt-3"><StarPicker value={rating} onChange={setRating} /></div>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Summary (optional)"
                className="mt-3 w-full rounded-lg border py-2 px-3 text-sm outline-none"
                style={{ borderColor: LINE, color: INK }}
              />
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Share your experience (optional)"
                rows={3}
                className="mt-2 w-full resize-none rounded-lg border py-2 px-3 text-sm outline-none"
                style={{ borderColor: LINE, color: INK }}
              />
              <div className="mt-3 flex items-center gap-2">
                <PrimaryButton onClick={submit} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Star className="h-4 w-4" />}
                  {data?.my_review ? "Update review" : "Submit review"}
                </PrimaryButton>
                {data?.my_review && (
                  <GhostButton onClick={removeReview}><Trash2 className="h-4 w-4" />Delete</GhostButton>
                )}
              </div>
            </div>

            <div className="space-y-3">
              {(data?.reviews || []).length === 0 ? (
                <p className="py-4 text-center text-sm" style={{ color: SUB }}>No reviews yet. Be the first!</p>
              ) : (
                (data?.reviews || []).map((r) => (
                  <div key={r.id} className="rounded-xl border p-4" style={{ borderColor: LINE }}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Stars value={r.rating} size={13} />
                        {r.is_mine && <span className="text-xs font-semibold text-blue-600">You</span>}
                      </div>
                      <span className="text-xs" style={{ color: SUB }}>{r.author}</span>
                    </div>
                    {r.title && <p className="mt-1.5 text-sm font-semibold" style={{ color: INK }}>{r.title}</p>}
                    {r.body && <p className="mt-0.5 text-sm" style={{ color: SUB }}>{r.body}</p>}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
