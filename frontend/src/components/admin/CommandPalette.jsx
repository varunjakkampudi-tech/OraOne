import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, CornerDownLeft } from "lucide-react";
import { useAdminTheme } from "@/components/admin/adminKit";
import { ADMIN_NAV_FLAT } from "@/components/admin/adminNav";

export default function CommandPalette({ open, onClose }) {
  const { t } = useAdminTheme();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return ADMIN_NAV_FLAT;
    return ADMIN_NAV_FLAT.filter(
      (it) => it.label.toLowerCase().includes(term) || it.group.toLowerCase().includes(term)
    );
  }, [q]);

  useEffect(() => {
    if (active >= results.length) setActive(0);
  }, [results, active]);

  if (!open) return null;

  const go = (it) => {
    if (!it) return;
    navigate(it.to);
    onClose();
  };

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); go(results[active]); }
    else if (e.key === "Escape") { onClose(); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-xl overflow-hidden rounded-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ background: t.glassSolid, border: `1px solid ${t.line}`, boxShadow: t.shadow }}
      >
        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: `1px solid ${t.line}` }}>
          <Search className="h-4 w-4" style={{ color: t.sub }} />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            placeholder="Jump to… (type a page name)"
            className="w-full bg-transparent text-sm outline-none"
            style={{ color: t.ink }}
          />
          <kbd className="rounded px-1.5 py-0.5 text-[10px]" style={{ background: t.hover, color: t.muted }}>ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2 scrollbar-thin">
          {results.length === 0 ? (
            <div className="px-3 py-6 text-center text-sm" style={{ color: t.sub }}>No matches</div>
          ) : (
            results.map((it, i) => (
              <button
                key={it.to}
                onMouseEnter={() => setActive(i)}
                onClick={() => go(it)}
                className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition"
                style={{ background: i === active ? t.hover : "transparent", color: t.ink }}
              >
                <span className="flex items-center gap-2.5">
                  <it.icon className="h-4 w-4" style={{ color: t.brand }} />
                  {it.label}
                  <span className="text-[11px]" style={{ color: t.muted }}>· {it.group}</span>
                </span>
                {i === active ? <CornerDownLeft className="h-3.5 w-3.5" style={{ color: t.muted }} /> : null}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
