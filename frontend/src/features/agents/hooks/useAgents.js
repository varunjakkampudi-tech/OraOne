/**
 * Agents domain — TanStack Query hooks. Pages call these, never the
 * service or API client directly (Router/Page -> hook -> service -> API).
 * Mutations invalidate the list query instead of every caller re-fetching
 * manually with its own `load()` — one cache, one source of truth.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentsService } from "@/services/api/agentsService";

const agentKeys = {
  all: ["agents"],
  lists: () => [...agentKeys.all, "list"],
  list: (params) => [...agentKeys.lists(), params],
  detail: (id) => [...agentKeys.all, "detail", id],
};

export function useAgents(params = {}) {
  return useQuery({
    queryKey: agentKeys.list(params),
    queryFn: () => agentsService.list(params),
    staleTime: 30_000,
  });
}

export function useAgent(id, options = {}) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => agentsService.get(id),
    enabled: Boolean(id) && options.enabled !== false,
  });
}

function useInvalidateAgents() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: agentKeys.all });
}

export function useCreateAgent() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: (payload) => agentsService.create(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateAgent() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: ({ id, payload }) => agentsService.update(id, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteAgent() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: (id) => agentsService.remove(id),
    onSuccess: invalidate,
  });
}

export function useDuplicateAgent() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: (id) => agentsService.duplicate(id),
    onSuccess: invalidate,
  });
}

export function useBulkUpdateAgentStatus() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: ({ ids, status }) => agentsService.bulkUpdateStatus(ids, status),
    onSuccess: invalidate,
  });
}

export function useBulkDeleteAgents() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: (ids) => agentsService.bulkRemove(ids),
    onSuccess: invalidate,
  });
}
