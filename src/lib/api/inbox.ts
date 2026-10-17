import { apiRequest } from "./client";

// Conversations are scoped to the organization. Each row is one chat thread
// with an assistant (agent).

export type ConversationSummary = {
  id: string;
  agent_id: string;
  /** Optional: the channel the conversation came from (e.g. "chat", "whatsapp"). Missing means website. */
  channel?: string | null;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  is_archived: boolean;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  created_at: string;
};

export function listConversations(limit = 100) {
  return apiRequest<ConversationSummary[]>(`/conversations?limit=${limit}&sort=recent`);
}

export function getConversation(conversationId: string) {
  return apiRequest<ConversationSummary>(`/conversations/${conversationId}`);
}

export function listMessages(conversationId: string) {
  return apiRequest<Message[]>(`/conversations/${conversationId}/messages?limit=500`);
}
