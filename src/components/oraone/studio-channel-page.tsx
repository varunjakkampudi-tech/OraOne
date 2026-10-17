import { Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  CHANNEL_PAGE_LABEL,
  CHANNEL_SETUP,
  channelPageStatus,
  channelSteps,
  isChannelPageKey,
  type ChannelPageKey,
} from "@/lib/studio-os";
import { CHANNEL_SETTINGS } from "@/lib/channel-settings";
import { ChannelChecklist } from "./studio-channel-checklist";
import { StudioChannelSettings } from "./studio-channel-settings";
import { StudioFrame } from "./studio";
import { ErrorNotice, Notice, PageHeader } from "./studio-ui";
import { useStudioAgent } from "@/lib/studio-agent";
import { StatusPill } from "./studio-os";

// One setup page per channel at /studio/channels/<name>. The checklist is data-driven:
// nothing is shown as done unless the channels or deploy records say so.

export function StudioChannelPage({ channel }: { channel: string }) {
  if (!isChannelPageKey(channel)) {
    return (
      <StudioFrame>
        <Notice kind="error">This setup page doesn't exist.</Notice>
        <Button asChild variant="outline" className="mt-4">
          <Link to="/studio">
            <ArrowLeft />
            Back to OraOne OS
          </Link>
        </Button>
      </StudioFrame>
    );
  }
  return <ChannelSetup channel={channel} />;
}

function ChannelSetup({ channel }: { channel: ChannelPageKey }) {
  const view = useStudioAgent({ withDeploy: channel === "website-chat" });
  const setup = CHANNEL_SETUP[channel];
  const steps = channelSteps(channel, view.facts);
  const loading = view.facts.state === "loading";
  const status =
    view.facts.state === "ready" && view.facts.channels
      ? channelPageStatus(channel, view.facts.channels)
      : null;
  const apiKey = CHANNEL_SETTINGS[channel].apiKey;
  const channelRow =
    view.facts.state === "ready" && view.facts.channels
      ? view.facts.channels.find((item) => item.channel === apiKey)
      : undefined;

  return (
    <StudioFrame>
      <Link to="/studio" className="inline-flex items-center gap-1 text-sm">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to OraOne OS
      </Link>
      <div className="mt-2">
        <PageHeader
          title={setup.title}
          description={setup.intro}
          action={
            status ? (
              <StatusPill status={status} />
            ) : loading ? (
              <span className="status-pill is-planned">Checking…</span>
            ) : (
              <span className="status-pill is-planned">Not connected yet</span>
            )
          }
        />
      </div>
      {view.error && (
        <div className="mt-4">
          <ErrorNotice message={view.error} />
        </div>
      )}
      <div className="mt-8">
        <ChannelChecklist
          needs={setup.needs}
          steps={steps}
          loading={loading}
          nextLink={{ to: "/studio/assistants", label: "Open AI Studio" }}
        />
      </div>
      <div className="mt-8">
        {loading ? null : view.facts.state === "unknown" ? (
          <Notice kind="error">
            Connection settings can't load right now. Try again in a moment.
          </Notice>
        ) : (
          <StudioChannelSettings
            key={channel}
            channel={channel}
            agentId={view.agentId}
            row={channelRow}
            onChanged={view.reload}
          />
        )}
      </div>
      <p className="mt-6 text-sm text-muted-foreground">
        {CHANNEL_PAGE_LABEL[channel]} setup shows what the app can confirm. Steps stay open until
        the app has data for them.
      </p>
    </StudioFrame>
  );
}
