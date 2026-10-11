import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronsUpDown, FolderKanban, Plus, Settings2 } from "lucide-react";
import { useProjects } from "@/lib/projects";

const DOT_COLORS = ["#2563EB", "#06B6D4", "#0EA5E9", "#F59E0B", "#10B981", "#EF4444", "#EC4899"];

function colorFor(project, index) {
  return project?.color || DOT_COLORS[index % DOT_COLORS.length];
}

/**
 * Project switcher — sits at the top of the sidebar. Lets the user change the
 * active project (workspace > project layer). Switching reloads the app scoped
 * to the chosen project.
 */
export default function ProjectSwitcher({ onNavigate = () => {} }) {
  const { projects, activeProject, switchProject, loading } = useProjects();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const nav = useNavigate();

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const goManage = () => {
    setOpen(false);
    onNavigate();
    nav("/app/projects");
  };

  const goNew = () => {
    setOpen(false);
    onNavigate();
    nav("/app/projects", { state: { openCreate: true } });
  };

  if (loading && !activeProject) {
    return (
      <div className="mx-3 mt-3 h-11 rounded-xl bg-[#F1F5F9] animate-pulse" data-testid="project-switcher-loading" />
    );
  }

  if (!activeProject) {
    return (
      <button
        onClick={goManage}
        className="mx-3 mt-3 flex w-[calc(100%-1.5rem)] items-center gap-2 rounded-xl border border-dashed border-[#CBD5E1] px-3 py-2.5 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
        data-testid="project-switcher-empty"
      >
        <Plus size={16} />
        Create a project
      </button>
    );
  }

  return (
    <div className="relative mx-3 mt-3" ref={ref} data-testid="project-switcher">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2.5 text-left transition-colors hover:bg-[#F8FAFC]"
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid="project-switcher-trigger"
      >
        <span
          className="grid size-7 flex-shrink-0 place-items-center rounded-lg text-white"
          style={{ background: colorFor(activeProject, 0) }}
        >
          <FolderKanban size={15} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
            Project
          </span>
          <span className="block truncate text-sm font-semibold text-[#0F172A]">
            {activeProject.name}
          </span>
        </span>
        <ChevronsUpDown size={15} className="flex-shrink-0 text-[#94A3B8]" />
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 top-[calc(100%+0.375rem)] z-50 overflow-hidden rounded-xl border border-[#E2E8F0] bg-white shadow-xl"
          role="listbox"
          data-testid="project-switcher-menu"
        >
          <div className="border-b border-[#F1F5F9] px-3 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
              Switch project
            </span>
          </div>
          <div className="max-h-64 overflow-y-auto p-1.5 scrollbar-thin">
            {projects.map((p, i) => {
              const active = p.id === activeProject.id;
              return (
                <button
                  key={p.id}
                  onClick={() => {
                    setOpen(false);
                    switchProject(p.id);
                  }}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors ${
                    active ? "bg-[#EFF6FF]" : "hover:bg-[#F8FAFC]"
                  }`}
                  role="option"
                  aria-selected={active}
                >
                  <span
                    className="grid size-6 flex-shrink-0 place-items-center rounded-md text-white"
                    style={{ background: colorFor(p, i) }}
                  >
                    <FolderKanban size={13} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-[#0F172A]">{p.name}</span>
                    <span className="block text-[11px] text-[#94A3B8]">
                      {p.is_default ? "Default · " : ""}
                      {p.resource_counts?.agents ?? 0} {(p.resource_counts?.agents ?? 0) === 1 ? "agent" : "agents"}
                    </span>
                  </span>
                  {active && <Check size={15} className="flex-shrink-0 text-[#2563EB]" />}
                </button>
              );
            })}
          </div>
          <div className="border-t border-[#E2E8F0] p-1.5">
            <button
              onClick={goNew}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm font-medium text-[#2563EB] hover:bg-[#EFF6FF]"
              data-testid="project-switcher-new"
            >
              <Plus size={15} />
              New project
            </button>
            <button
              onClick={goManage}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
              data-testid="project-switcher-manage"
            >
              <Settings2 size={15} />
              Manage projects
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
