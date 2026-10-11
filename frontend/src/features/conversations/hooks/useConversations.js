/**
 * Conversations domain — TanStack Query hooks.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { conversationsService } from "@/services/api/conversationsService";

const conversationKeys = {
  all: ["conversations"],
  lists: () => [...conversationKeys.all, "list"],
  list: (params) => [...conversationKeys.lists(), params],
  detail: (id) => [...conversationKeys.all, "detail", id],
  messages: (id) => [...conversationKeys.all, "messages", id],
};

export function useConversations(params = {}) {
  return useQuery({
    queryKey: conversationKeys.list(params),
    queryFn: () => conversationsService.list(params),
    staleTime: 15_000,
  });
}

export function useConversationMessages(id) {
  return useQuery({
    queryKey: conversationKeys.messages(id),
    queryFn: () => conversationsService.messages(id),
    enabled: Boolean(id),
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => conversationsService.sendMessage(id, payload),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: conversationKeys.messages(id) });
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
    },
  });
}

export function useUpdateConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => conversationsService.update(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: conversationKeys.all }),
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => conversationsService.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: conversationKeys.lists() }),
  });
}
