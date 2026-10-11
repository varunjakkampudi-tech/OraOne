import React, { useMemo, useState, useRef, useEffect } from "react";
import {
  Search,
  ArrowUp,
  ArrowDown,
  ChevronsUpDown,
  SlidersHorizontal,
  Columns3,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Check,
} from "lucide-react";
import { cx } from "./kit";

/* ──────────────────────────────────────────────────────────────────────────
   DataTable — one enterprise table for the whole product.
   Features: search, filters, sort, column visibility, pagination,
   bulk actions, row actions, sticky header, row-click (drawer integration).
   Everything else configures it via `columns`, `rows`, and handlers.

   columns: [{ key, header, render?(row), sortable?, accessor?(row), className?, minWidth? }]
   ────────────────────────────────────────────────────────────────────────── */

function useOutsideClose(ref, onClose) {
  useEffect(() => {
    const h = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [ref, onClose]);
}

function Menu({ button, children, align = "right" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useOutsideClose(ref, () => setOpen(false));
  return (
    <div className="relative" ref={ref}>
      {React.cloneElement(button, { onClick: () => setOpen((v) => !v) })}
      {open && (
        <div
          className={cx(
            "absolute z-30 mt-1.5 min-w-[190px] rounded-xl border border-line bg-white p-1.5 shadow-pop",
            align === "right" ? "right-0" : "left-0"
          )}
          onClick={() => setOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export function MenuItem({ icon: Icon, children, danger, ...rest }) {
  return (
    <button
      className={cx(
        "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium transition-colors",
        danger ? "text-danger hover:bg-danger-soft" : "text-body hover:bg-canvas"
      )}
      {...rest}
    >
      {Icon && <Icon size={15} className="shrink-0" />}
      {children}
    </button>
  );
}

export default function DataTable({
  columns,
  rows,
  rowKey = (r) => r.id,
  onRowClick,
  search = true,
  searchPlaceholder = "Search…",
  searchKeys,
  filters = [], // [{ key, label, options:[{value,label}], accessor?(row) }]
  bulkActions, // (selectedRows, clear) => ReactNode
  rowActions, // (row) => ReactNode (menu items)
  pageSize = 10,
  toolbarExtra,
  emptyState,
  stickyHeader = true,
}) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState({ key: null, dir: "asc" });
  const [activeFilters, setActiveFilters] = useState({});
  const [hidden, setHidden] = useState({});
  const [selected, setSelected] = useState({});
  const [page, setPage] = useState(1);

  const visibleCols = columns.filter((c) => !hidden[c.key]);

  const accessor = (col, row) =>
    col.accessor ? col.accessor(row) : row[col.key];

  const filtered = useMemo(() => {
    let out = rows || [];
    // search
    if (q.trim()) {
      const needle = q.toLowerCase();
      const keys = searchKeys || columns.map((c) => c.key);
      out = out.filter((r) =>
        keys.some((k) => String(r[k] ?? "").toLowerCase().includes(needle))
      );
    }
    // filters
    for (const f of filters) {
      const val = activeFilters[f.key];
      if (val != null && val !== "") {
        out = out.filter((r) => String(f.accessor ? f.accessor(r) : r[f.key]) === String(val));
      }
    }
    // sort
    if (sort.key) {
      const col = columns.find((c) => c.key === sort.key);
      out = [...out].sort((a, b) => {
        const av = accessor(col, a);
        const bv = accessor(col, b);
        if (av == null) return 1;
        if (bv == null) return -1;
        const cmp =
          typeof av === "number" && typeof bv === "number"
            ? av - bv
            : String(av).localeCompare(String(bv));
        return sort.dir === "asc" ? cmp : -cmp;
      });
    }
    return out;
  }, [rows, q, activeFilters, sort, columns, filters, searchKeys]); // eslint-disable-line

  // reset to page 1 when the result set changes
  useEffect(() => {
    setPage(1);
  }, [q, activeFilters, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice((page - 1) * pageSize, page * pageSize);

  const selectedRows = (rows || []).filter((r) => selected[rowKey(r)]);
  const allOnPageSelected = pageRows.length > 0 && pageRows.every((r) => selected[rowKey(r)]);

  const toggleAllOnPage = () => {
    const next = { ...selected };
    if (allOnPageSelected) pageRows.forEach((r) => delete next[rowKey(r)]);
    else pageRows.forEach((r) => (next[rowKey(r)] = true));
    setSelected(next);
  };
  const clearSelection = () => setSelected({});

  const toggleSort = (col) => {
    if (!col.sortable) return;
    setSort((s) =>
      s.key === col.key
        ? { key: col.key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key: col.key, dir: "asc" }
    );
  };

  const hasToolbar = search || filters.length > 0 || bulkActions || toolbarExtra;

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      {hasToolbar && (
        <div className="flex flex-wrap items-center gap-2">
          {search && (
            <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={searchPlaceholder}
                type="search"
                aria-label={searchPlaceholder}
                className="h-9 w-full rounded-full border border-stroke bg-white pl-9 pr-3 text-[13.5px] text-ink outline-none placeholder:text-faint focus:border-brand focus-visible:ring-2 focus-visible:ring-brand/25"
              />
            </div>
          )}

          {filters.map((f) => (
            <select
              key={f.key}
              value={activeFilters[f.key] ?? ""}
              onChange={(e) => setActiveFilters((s) => ({ ...s, [f.key]: e.target.value }))}
              aria-label={`Filter by ${f.label}`}
              className="h-9 rounded-full border border-stroke bg-white px-3 text-[13px] font-medium text-body outline-none focus:border-brand focus-visible:ring-2 focus-visible:ring-brand/25"
            >
              <option value="">{f.label}: All</option>
              {f.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ))}

          {filters.length > 0 && Object.values(activeFilters).some((v) => v) && (
            <button
              onClick={() => setActiveFilters({})}
              className="inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-[13px] font-semibold text-sub hover:text-ink"
            >
              <SlidersHorizontal size={14} /> Clear
            </button>
          )}

          <div className="ml-auto flex items-center gap-2">
            {toolbarExtra}
            {/* Column visibility */}
            <Menu
              button={
                <button className="inline-flex h-9 items-center gap-1.5 rounded-full border border-stroke bg-white px-3 text-[13px] font-semibold text-body hover:bg-wash">
                  <Columns3 size={14} /> Columns
                </button>
              }
            >
              {columns.map((c) => (
                <button
                  key={c.key}
                  onClick={(e) => {
                    e.stopPropagation();
                    setHidden((h) => ({ ...h, [c.key]: !h[c.key] }));
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-body hover:bg-canvas"
                >
                  <span className={cx("grid size-4 place-items-center rounded border", hidden[c.key] ? "border-[#CBD5E1]" : "border-brand bg-brand text-white")}>
                    {!hidden[c.key] && <Check size={11} />}
                  </span>
                  {c.header}
                </button>
              ))}
            </Menu>
          </div>
        </div>
      )}

      {/* Bulk action bar */}
      {bulkActions && selectedRows.length > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-[#DBE7FF] bg-brand-soft px-4 py-2.5">
          <span className="text-[13px] font-semibold text-brand-hover">{selectedRows.length} selected</span>
          <div className="flex items-center gap-2">{bulkActions(selectedRows, clearSelection)}</div>
          <button onClick={clearSelection} className="ml-auto text-[13px] font-semibold text-sub hover:text-ink">
            Clear
          </button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-card">
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full border-collapse text-left">
            <thead className={cx(stickyHeader && "sticky top-0 z-10", "bg-subtle")}>
              <tr className="border-b border-line">
                {bulkActions && (
                  <th scope="col" className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={allOnPageSelected}
                      onChange={toggleAllOnPage}
                      aria-label="Select all rows on this page"
                      className="size-4 cursor-pointer rounded border-[#CBD5E1] accent-brand focus-visible:ring-2 focus-visible:ring-brand/40"
                    />
                  </th>
                )}
                {visibleCols.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    onClick={() => toggleSort(col)}
                    onKeyDown={(e) => {
                      if (col.sortable && (e.key === "Enter" || e.key === " ")) {
                        e.preventDefault();
                        toggleSort(col);
                      }
                    }}
                    tabIndex={col.sortable ? 0 : undefined}
                    role={col.sortable ? "button" : undefined}
                    aria-sort={
                      col.sortable
                        ? sort.key === col.key
                          ? sort.dir === "asc"
                            ? "ascending"
                            : "descending"
                          : "none"
                        : undefined
                    }
                    style={{ minWidth: col.minWidth }}
                    className={cx(
                      "px-4 py-3 text-[11.5px] font-semibold uppercase tracking-[0.06em] text-sub",
                      col.sortable &&
                        "cursor-pointer select-none hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand/30",
                      col.className
                    )}
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {col.header}
                      {col.sortable &&
                        (sort.key !== col.key ? (
                          <ChevronsUpDown size={13} className="text-[#CBD5E1]" />
                        ) : sort.dir === "asc" ? (
                          <ArrowUp size={13} className="text-brand" />
                        ) : (
                          <ArrowDown size={13} className="text-brand" />
                        ))}
                    </span>
                  </th>
                ))}
                {rowActions && <th className="w-12 px-4 py-3" />}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => {
                const key = rowKey(row);
                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    onKeyDown={
                      onRowClick
                        ? (e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              onRowClick(row);
                            }
                          }
                        : undefined
                    }
                    tabIndex={onRowClick ? 0 : undefined}
                    role={onRowClick ? "button" : undefined}
                    className={cx(
                      "border-b border-hairline transition-colors last:border-0",
                      onRowClick &&
                        "cursor-pointer hover:bg-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand/30",
                      selected[key] && "bg-[#F5F9FF]"
                    )}
                  >
                    {bulkActions && (
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={!!selected[key]}
                          onChange={() => setSelected((s) => ({ ...s, [key]: !s[key] }))}
                          aria-label="Select row"
                          className="size-4 cursor-pointer rounded border-[#CBD5E1] accent-brand focus-visible:ring-2 focus-visible:ring-brand/40"
                        />
                      </td>
                    )}
                    {visibleCols.map((col) => (
                      <td key={col.key} className={cx("px-4 py-3 text-[13.5px] text-body", col.cellClassName)}>
                        {col.render ? col.render(row) : String(accessor(col, row) ?? "—")}
                      </td>
                    ))}
                    {rowActions && (
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <Menu
                          button={
                            <button aria-label="Row actions" className="grid size-8 place-items-center rounded-full text-faint hover:bg-hairline hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40">
                              <MoreHorizontal size={17} />
                            </button>
                          }
                        >
                          {rowActions(row)}
                        </Menu>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Empty inside table frame */}
        {pageRows.length === 0 && <div className="px-4 py-10">{emptyState}</div>}

        {/* Pagination */}
        {filtered.length > pageSize && (
          <div className="flex items-center justify-between border-t border-line px-4 py-3">
            <p className="text-[12.5px] text-sub">
              {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, filtered.length)} of {filtered.length}
            </p>
            <div className="flex items-center gap-1">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="grid size-8 place-items-center rounded-lg border border-stroke text-body disabled:opacity-40 hover:bg-wash"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="px-2 text-[12.5px] font-semibold text-body">
                {page} / {totalPages}
              </span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="grid size-8 place-items-center rounded-lg border border-stroke text-body disabled:opacity-40 hover:bg-wash"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
