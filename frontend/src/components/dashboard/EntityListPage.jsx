import React from "react";
import { PageHeader } from "./kit";
import DataTable from "./DataTable";
import { TableSkeleton, ErrorState, EmptyState } from "./states";

/* ──────────────────────────────────────────────────────────────────────────
   EntityListPage — the standard scaffold for every list/module screen.
   Composes: PageHeader → (loading | error | empty | DataTable).
   A module becomes configuration instead of custom layout code.

   Usage:
     <EntityListPage
       eyebrow="Agents" title="AI Agents" subtitle="…" icon={Bot}
       actions={<PrimaryButton>…</PrimaryButton>}
       loading={loading} error={error} onRetry={load}
       rows={rows} columns={columns}
       empty={{ icon, title, hint, action }}
       search filters={…} rowActions={…} bulkActions={…}
       onRowClick={openDrawer}
     >
       {drawer}
     </EntityListPage>
   ────────────────────────────────────────────────────────────────────────── */

export default function EntityListPage({
  // header
  eyebrow,
  title,
  subtitle,
  icon,
  actions,
  // async state
  loading,
  error,
  onRetry,
  // data + table config
  rows = [],
  columns,
  empty,
  stats, // optional KPI strip rendered between header and table
  skeletonCols = 4,
  children, // e.g. mounted <Drawer/>
  ...tableProps
}) {
  const emptyNode = empty ? <EmptyState {...empty} /> : null;

  return (
    <div className="space-y-6" data-testid="entity-list-page">
      <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} icon={icon} actions={actions} />

      {stats}

      {loading ? (
        <TableSkeleton rows={6} cols={skeletonCols} />
      ) : error ? (
        <ErrorState message={typeof error === "string" ? error : undefined} onRetry={onRetry} />
      ) : rows.length === 0 ? (
        emptyNode
      ) : (
        <DataTable rows={rows} columns={columns} emptyState={emptyNode} {...tableProps} />
      )}

      {children}
    </div>
  );
}
