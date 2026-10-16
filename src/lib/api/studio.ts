import { apiRequest } from "./client";

// Studio maps onto the backend's tenancy model:
//   workspace  -> project (scoped per organization)
//   assistant  -> agent of type "chat", scoped to a project
//   playground -> conversation with that agent

export type Project = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  status: string;
  is_default: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Agent = {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  type: string;
  status: string;
  model: string;
  system_prompt: string | null;
  temperature: number;
  language: string;
  greeting: string | null;
  max_tokens: number;
};

export type AgentInput = {
  name?: string;
  type?: string;
  description?: string;
  status?: string;
  system_prompt?: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  created_at: string;
};

export type Conversation = { id: string; agent_id: string; title: string | null };

export type SendMessageResult = {
  conversation_id: string;
  assistant_message: ChatMessage;
};

export function listProjects() {
  return apiRequest<{ items: Project[]; total: number }>("/projects?limit=100");
}

export function createProject(input: { name: string }) {
  return apiRequest<Project>("/projects", { method: "POST", body: input });
}

export function updateProjectSettings(projectId: string, settings: Record<string, unknown>) {
  return apiRequest<Project>(`/projects/${projectId}`, { method: "PATCH", body: { settings } });
}

export function listAgents(projectId: string) {
  return apiRequest<{ items: Agent[]; total: number }>("/agents?limit=100&sort=-created_at", {
    projectId,
  });
}

export function createAgent(projectId: string, input: AgentInput & { name: string; type: string }) {
  return apiRequest<Agent>("/agents", { method: "POST", body: input, projectId });
}

export function getAgent(agentId: string) {
  return apiRequest<Agent>(`/agents/${agentId}`);
}

export function updateAgent(agentId: string, input: AgentInput) {
  return apiRequest<Agent>(`/agents/${agentId}`, { method: "PUT", body: input });
}

export function createConversation(agentId: string, title: string) {
  return apiRequest<Conversation>("/conversations", {
    method: "POST",
    body: { agent_id: agentId, title },
  });
}

export function sendMessage(conversationId: string, content: string) {
  return apiRequest<SendMessageResult>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: { content },
  });
}
