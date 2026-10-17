import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  rotateAgentChannelSecret,
  updateAgentChannel,
  type ChannelRead,
  type OneTimeSecret,
} from "@/lib/api/channels";
import { messageOf } from "@/lib/api/client";
import {
  CHANNEL_SETTINGS,
  validateChannelSettings,
  type SettingField,
} from "@/lib/channel-settings";
import type { ChannelPageKey } from "@/lib/studio-os";
import { Notice } from "./studio-ui";

// The settings form on a channel setup page. It saves only the identifiers the inbound path needs,
// plus the on/off switch. The server generates every secret and returns it once: this form shows
// it in a dialog and never keeps it. After each save the parent reloads the channel rows, so the
// checklist shows what the API now holds.

type Props = {
  channel: ChannelPageKey;
  agentId: string | null;
  row: ChannelRead | undefined;
  /** Called after a successful save or rotation so the parent re-reads the channel rows. */
  onChanged: () => void;
};

type Message = { kind: "success" | "error"; text: string };

export function StudioChannelSettings({ channel, agentId, row, onChanged }: Props) {
  const spec = CHANNEL_SETTINGS[channel];
  const headingId = useId();
  const [enabled, setEnabled] = useState(Boolean(row?.enabled));
  const [values, setValues] = useState<Partial<Record<SettingField, string>>>(() => {
    const initial: Partial<Record<SettingField, string>> = {};
    for (const field of spec.fields) {
      initial[field.key] =
        field.key === "phone_number"
          ? (row?.phone_number ?? "")
          : (row?.configuration?.[field.key] ?? "");
    }
    return initial;
  });
  const [errors, setErrors] = useState<Partial<Record<SettingField, string>>>({});
  const [message, setMessage] = useState<Message | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmingRotate, setConfirmingRotate] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [issued, setIssued] = useState<OneTimeSecret | null>(null);

  const maskedSecret = spec.hasSecret ? (row?.masked_secrets?.["sdk_secret"] ?? null) : null;
  const disabled = agentId === null;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agentId) return;
    const checked = validateChannelSettings(spec, values, enabled);
    if (!checked.ok) {
      setErrors(checked.errors);
      setMessage({ kind: "error", text: checked.message });
      return;
    }
    setErrors({});
    setSaving(true);
    setMessage(null);
    try {
      const saved = await updateAgentChannel(agentId, spec.apiKey, {
        enabled,
        ...(spec.fields.length > 0 ? { settings: checked.settings } : {}),
      });
      setMessage({ kind: "success", text: "Saved. The checklist above shows the new state." });
      onChanged();
      if (saved.one_time_secret) setIssued(saved.one_time_secret);
    } catch (err) {
      setMessage({
        kind: "error",
        text: messageOf(err, "Those settings couldn't be saved. Check them and try again."),
      });
    } finally {
      setSaving(false);
    }
  }

  async function rotate() {
    if (!agentId) return;
    setRotating(true);
    setMessage(null);
    try {
      const rotated = await rotateAgentChannelSecret(agentId, spec.apiKey);
      setConfirmingRotate(false);
      setIssued({ name: rotated.secret_name, value: rotated.secret, shown_once: true });
      onChanged();
    } catch (err) {
      setMessage({
        kind: "error",
        text: messageOf(err, "The secret couldn't be replaced. The current one still works."),
      });
    } finally {
      setRotating(false);
    }
  }

  return (
    <section
      aria-labelledby={headingId}
      className="grid gap-6 rounded-xl border border-border bg-card p-5"
    >
      <div className="grid gap-1">
        <h2 id={headingId} className="text-lg font-semibold">
          Connection settings
        </h2>
        <p className="text-sm text-muted-foreground">
          Only the details below are saved here. Secrets are created by OraOne and shown once.
        </p>
      </div>

      {disabled && (
        <Notice>Create an assistant in AI Studio before you set up this channel.</Notice>
      )}

      <form className="grid gap-6" onSubmit={save} noValidate>
        <fieldset disabled={disabled || saving} className="grid gap-6">
          {spec.fields.map((field) => {
            const inputId = `${headingId}-${field.key}`;
            const helpId = `${inputId}-help`;
            const errorId = `${inputId}-error`;
            const error = errors[field.key];
            return (
              <div key={field.key} className="grid gap-2">
                <Label htmlFor={inputId}>{field.label}</Label>
                <Input
                  id={inputId}
                  name={field.key}
                  inputMode={field.inputMode}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={field.placeholder}
                  value={values[field.key] ?? ""}
                  onChange={(event) => {
                    const next = event.target.value;
                    setValues((current) => ({ ...current, [field.key]: next }));
                  }}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? `${helpId} ${errorId}` : helpId}
                />
                <p id={helpId} className="text-sm text-muted-foreground">
                  {field.help}
                </p>
                {error && (
                  <p id={errorId} role="alert" className="text-sm text-destructive">
                    {error}
                  </p>
                )}
              </div>
            );
          })}

          <div className="flex items-start justify-between gap-4">
            <div className="grid gap-1">
              <Label htmlFor={`${headingId}-enabled`}>{spec.enableLabel}</Label>
              <p id={`${headingId}-enabled-help`} className="text-sm text-muted-foreground">
                {spec.enableHelp}
              </p>
            </div>
            <Switch
              id={`${headingId}-enabled`}
              checked={enabled}
              onCheckedChange={setEnabled}
              aria-describedby={`${headingId}-enabled-help`}
            />
          </div>

          <div>
            <Button type="submit" className="w-full sm:w-auto" disabled={disabled || saving}>
              {saving ? "Saving…" : "Save settings"}
            </Button>
          </div>
        </fieldset>
      </form>

      {message && (
        <p
          role={message.kind === "error" ? "alert" : "status"}
          className={`text-sm ${message.kind === "error" ? "text-destructive" : "text-muted-foreground"}`}
        >
          {message.text}
        </p>
      )}

      {spec.hasSecret && (
        <div className="grid gap-3 border-t border-border pt-5">
          <h3 className="text-base font-semibold">App secret</h3>
          {maskedSecret ? (
            <p className="text-sm">
              Current secret: <span className="font-mono">{maskedSecret}</span>. The full value is
              not shown again.
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              No secret yet. Turn on app access and save to create one.
            </p>
          )}

          {maskedSecret && !confirmingRotate && (
            <div>
              <Button
                variant="outline"
                className="w-full sm:w-auto"
                disabled={disabled || rotating}
                onClick={() => setConfirmingRotate(true)}
              >
                Replace secret
              </Button>
            </div>
          )}

          {maskedSecret && confirmingRotate && (
            <div
              role="group"
              aria-label="Confirm replacing the secret"
              className="grid gap-3 rounded-lg border border-destructive p-4"
            >
              <p className="text-sm">
                Replacing the secret stops the current one working straight away. Any app that still
                uses it will be refused until you give it the new secret.
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  variant="destructive"
                  className="w-full sm:w-auto"
                  disabled={rotating}
                  onClick={rotate}
                >
                  {rotating ? "Replacing…" : "Yes, replace the secret"}
                </Button>
                <Button
                  variant="outline"
                  className="w-full sm:w-auto"
                  disabled={rotating}
                  onClick={() => setConfirmingRotate(false)}
                >
                  Keep the current secret
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      <OneTimeSecretDialog secret={issued} onClose={() => setIssued(null)} />
    </section>
  );
}

function OneTimeSecretDialog({
  secret,
  onClose,
}: {
  secret: OneTimeSecret | null;
  onClose: () => void;
}) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  async function copy() {
    if (!secret) return;
    try {
      await navigator.clipboard.writeText(secret.value);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }

  return (
    <Dialog
      open={secret !== null}
      onOpenChange={(open) => {
        if (!open) {
          setCopyState("idle");
          onClose();
        }
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Copy your new secret now</DialogTitle>
          <DialogDescription>
            This is the only time this secret is shown. It will not be shown again. Store it in your
            secrets manager before you close this window. If you lose it, replace the secret to get
            a new one.
          </DialogDescription>
        </DialogHeader>
        <div
          className="break-all rounded-md border border-border bg-muted p-3 font-mono text-sm"
          aria-label="New secret"
          data-testid="one-time-secret"
        >
          {secret?.value}
        </div>
        <div className="grid gap-2">
          <Button
            variant="outline"
            className="w-full sm:w-auto sm:justify-self-start"
            onClick={copy}
          >
            Copy secret
          </Button>
          <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
            {copyState === "copied" && "Copied to your clipboard."}
            {copyState === "failed" &&
              "Copying didn't work. Select the secret above and copy it by hand."}
          </p>
        </div>
        <DialogFooter>
          <Button className="w-full sm:w-auto" onClick={onClose}>
            I have saved it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
