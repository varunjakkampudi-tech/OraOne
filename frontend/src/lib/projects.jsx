import React, { createContext, useContext, useCallback, useEffect, useMemo, useState } from "react";
import { api, getActiveProjectId, setActiveProjectId } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * Projects layer — Workspace (organization) > Project > Resources.
 *
 * Holds the list of projects for the current workspace and the active project.
 * The active project id is persisted (localStorage) and attached to every API
 * request as the `X-Project-Id` header (see lib/api.js), so the backend scopes
 * resources to it. Switching projects re-scopes the whole app, so we trigger a
 * full reload to guarantee every page re-fetches against the new project.
 */

const ProjectContext = createContext(null);

function pickActive(projects, storedId) {
  if (!projects || projects.length === 0) return null;
  if (storedId) {
    const match = projects.find((p) => p.id === storedId);
    if (match) return match;
  }
  return projects.find((p) => p.is_default) || projects[0];
}

export function ProjectProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!isAuthenticated) {
      setProjects([]);
      setActiveProject(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get("/projects");
      const items = data?.items || [];
      setProjects(items);
      const active = pickActive(items, getActiveProjectId());
      setActiveProject(active);
      // Keep storage in sync so the header is correct on the next request.
      if (active) setActiveProjectId(active.id);
    } catch (e) {
      setError(e);
      setProjects([]);
      setActiveProject(null);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    load();
  }, [load]);

  // Switch the active project. Persists immediately, then reloads so every
  // page re-fetches its data scoped to the newly-selected project.
  const switchProject = useCallback(
    (projectId) => {
      if (!projectId || projectId === activeProject?.id) return;
      const next = projects.find((p) => p.id === projectId);
      if (!next) return;
      setActiveProjectId(projectId);
      setActiveProject(next);
      // Hard reload to re-scope all in-flight/cached data across the app.
      window.location.reload();
    },
    [projects, activeProject]
  );

  const refreshProjects = useCallback(() => load(), [load]);

  const value = useMemo(
    () => ({
      projects,
      activeProject,
      activeProjectId: activeProject?.id || null,
      loading,
      error,
      switchProject,
      refreshProjects,
    }),
    [projects, activeProject, loading, error, switchProject, refreshProjects]
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjects() {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error("useProjects must be used within a ProjectProvider");
  }
  return ctx;
}
