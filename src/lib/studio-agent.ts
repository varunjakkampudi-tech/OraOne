import { useCallback, useEffect, useState } from "react";
import { messageOf } from "@/lib/api/client";
import {
  getAgentDeploy,
  listAgentChannels,
  type ChannelRead,
  type DeployInfo,
} from "@/lib/api/channels";
import { listAgents, listProjects } from "@/lib/api/studio";
import type { ChannelLoad, DeployFacts, SetupFacts } from "@/lib/studio-os";

// Read-only lookup behind the OraOne OS hub and the channel setup pages: the first workspace,
// its first assistant, that assistant's channel rows and, when asked, its deploy record.
// A failed request leaves the matching facts unknown instead of reading as "not done".

export type StudioAgentView = {
  facts: SetupFacts;
  channels: ChannelLoad;
  agentId: string | null;
  agentName: string | null;
  /** A plain message when part of the lookup failed; empty when everything loaded. */
  error: string;
};

export type StudioAgentHook = StudioAgentView & {
  /** Reads the channel rows again, for example after a save. The old rows stay until the new ones arrive. */
  reload: () => void;
};

const LOADING: StudioAgentView = {
  facts: { state: "loading" },
  channels: { state: "loading" },
  agentId: null,
  agentName: null,
  error: "",
};

function unknown(error: string): StudioAgentView {
  return {
    facts: { state: "unknown" },
    channels: { state: "unavailable" },
    agentId: null,
    agentName: null,
    error,
  };
}

const NO_ASSISTANT: StudioAgentView = {
  facts: { state: "no-assistant" },
  channels: { state: "unavailable" },
  agentId: null,
  agentName: null,
  error: "",
};

export async function loadStudioAgent(withDeploy: boolean): Promise<StudioAgentView> {
  let projectId: string | undefined;
  try {
    const { items } = await listProjects();
    projectId = items[0]?.id;
  } catch (err) {
    return unknown(messageOf(err, "Couldn't load your workspace."));
  }
  if (!projectId) return NO_ASSISTANT;

  let agent: { id: string; name: string } | undefined;
  try {
    const { items } = await listAgents(projectId);
    agent = items[0];
  } catch (err) {
    return unknown(messageOf(err, "Couldn't load your assistants."));
  }
  if (!agent) return NO_ASSISTANT;

  const channels: ChannelRead[] | null = await listAgentChannels(agent.id).then(
    (response) => response.items,
    () => null,
  );
  const deploy: DeployFacts | null = withDeploy
    ? await getAgentDeploy(agent.id).then(
        (info: DeployInfo) => info,
        () => null,
      )
    : null;

  return {
    facts: { state: "ready", channels, deploy },
    channels: channels ? { state: "ready", items: channels } : { state: "unavailable" },
    agentId: agent.id,
    agentName: agent.name,
    error: channels
      ? ""
      : "Couldn't load the channel status. The statuses below may be out of date.",
  };
}

export function useStudioAgent({
  withDeploy = false,
}: { withDeploy?: boolean } = {}): StudioAgentHook {
  const [view, setView] = useState<StudioAgentView>(LOADING);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loadStudioAgent(withDeploy).then((next) => {
      if (!cancelled) setView(next);
    });
    return () => {
      cancelled = true;
    };
  }, [withDeploy, version]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);

  return { ...view, reload };
}
