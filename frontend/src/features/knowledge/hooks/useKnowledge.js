/**
 * Knowledge base domain — TanStack Query hooks.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knowledgeService } from "@/services/api/knowledgeService";

const knowledgeKeys = {
  all: ["knowledge-bases"],
  lists: () => [...knowledgeKeys.all, "list"],
  detail: (id) => [...knowledgeKeys.all, "detail", id],
  documents: (id) => [...knowledgeKeys.all, "documents", id],
};

export function useKnowledgeBases(params = {}) {
  return useQuery({
    queryKey: [...knowledgeKeys.lists(), params],
    queryFn: () => knowledgeService.listBases(params),
    staleTime: 30_000,
  });
}

export function useKnowledgeBase(id) {
  return useQuery({
    queryKey: knowledgeKeys.detail(id),
    queryFn: () => knowledgeService.getBase(id),
    enabled: Boolean(id),
  });
}

export function useKnowledgeDocuments(baseId) {
  return useQuery({
    queryKey: knowledgeKeys.documents(baseId),
    queryFn: () => knowledgeService.listDocuments(baseId),
    enabled: Boolean(baseId),
  });
}

export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => knowledgeService.createBase(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() }),
  });
}

export function useDeleteKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => knowledgeService.removeBase(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() }),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ baseId, file, extra }) => knowledgeService.uploadDocument(baseId, file, extra),
    onSuccess: (_data, { baseId }) => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents(baseId) });
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.detail(baseId) });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ baseId, docId }) => knowledgeService.removeDocument(baseId, docId),
    onSuccess: (_data, { baseId }) => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents(baseId) });
    },
  });
}
