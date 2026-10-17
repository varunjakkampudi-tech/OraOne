import { useId, useState, type ChangeEvent } from "react";
import { Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { messageOf } from "@/lib/api/client";
import {
  commitLeadImport,
  previewLeadImport,
  type LeadImportPreview,
  type LeadImportResult,
  type LeadImportStatus,
} from "@/lib/api/leads";
import { ErrorNotice, Notice } from "./studio-ui";

// Client-side checks are only a convenience. The server re-checks size, type and content.
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];
const PREVIEW_ROW_LIMIT = 200;

const STATUS_LABEL: Record<LeadImportStatus, string> = {
  valid: "Ready",
  duplicate_existing: "Already a lead",
  duplicate_in_file: "Repeated in file",
  invalid: "Needs fixing",
};

const STATUS_CLASS: Record<LeadImportStatus, string> = {
  valid: "bg-accent text-accent-foreground",
  duplicate_existing: "bg-muted text-muted-foreground",
  duplicate_in_file: "bg-muted text-muted-foreground",
  invalid: "bg-destructive text-destructive-foreground",
};

function fileProblem(file: File): string {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return "Choose a .csv or .xlsx file. Macro-enabled workbooks (.xlsm) aren't accepted.";
  }
  if (file.size > MAX_FILE_BYTES) {
    return "This file is larger than 5 MB. Split it into smaller files and try again.";
  }
  if (file.size === 0) return "This file is empty.";
  return "";
}

type Props = {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported: () => void;
};

/** Import contacts: choose a file, review the preview, then confirm. Nothing is saved before confirm. */
export function LeadImportDialog({ projectId, open, onOpenChange, onImported }: Props) {
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [preview, setPreview] = useState<LeadImportPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<LeadImportResult | null>(null);

  function reset() {
    setFile(null);
    setFileError("");
    setPreview(null);
    setPreviewing(false);
    setSaving(false);
    setError("");
    setResult(null);
  }

  function handleOpenChange(next: boolean) {
    if (!next && saving) return; // keep the dialog open while a save is in flight
    if (!next) reset();
    onOpenChange(next);
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null;
    setPreview(null);
    setError("");
    setResult(null);
    if (!chosen) {
      setFile(null);
      setFileError("");
      return;
    }
    const problem = fileProblem(chosen);
    setFileError(problem);
    setFile(problem ? null : chosen);
  }

  async function runPreview() {
    if (!file) return;
    setPreviewing(true);
    setError("");
    try {
      setPreview(await previewLeadImport(projectId, file));
    } catch (err) {
      setError(messageOf(err, "Couldn't check this file. Try again."));
    } finally {
      setPreviewing(false);
    }
  }

  async function confirmSave() {
    if (!file || !preview) return;
    setSaving(true);
    setError("");
    try {
      const saved = await commitLeadImport(projectId, file);
      setResult(saved);
      setPreview(null);
      setFile(null);
      onImported();
    } catch (err) {
      setError(messageOf(err, "Nothing was saved. Check the file and try again."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[90vh] w-[calc(100vw-2rem)] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Import contacts</DialogTitle>
          <DialogDescription>
            Upload a CSV or Excel file. You'll see a preview before anything is saved.
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <div className="grid gap-4">
            <Notice>
              Saved {result.saved} {result.saved === 1 ? "contact" : "contacts"}. Skipped{" "}
              {result.skipped_duplicate_existing + result.skipped_duplicate_in_file} duplicate
              {result.skipped_duplicate_existing + result.skipped_duplicate_in_file === 1
                ? ""
                : "s"}{" "}
              and {result.skipped_invalid} invalid {result.skipped_invalid === 1 ? "row" : "rows"}.
            </Notice>
            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)}>Done</Button>
            </DialogFooter>
          </div>
        ) : !preview ? (
          <div className="grid gap-4">
            <div className="grid gap-2 text-sm text-muted-foreground">
              <p>
                Up to 5,000 rows and 5 MB. Columns are matched by name: Name, Phone, Email, Company,
                Notes, and an optional Consent column (yes, no, or blank for unknown). Each contact
                needs a phone number or an email address.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label
                htmlFor={inputId}
                className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
              >
                <Upload className="size-4" aria-hidden="true" />
                Choose file
                <input
                  id={inputId}
                  type="file"
                  accept={ACCEPTED_EXTENSIONS.join(",")}
                  className="sr-only"
                  onChange={chooseFile}
                />
              </label>
              <span className="min-w-0 break-all text-sm">
                {file ? file.name : "No file chosen"}
              </span>
            </div>
            {fileError && <Notice kind="error">{fileError}</Notice>}
            {error && (
              <ErrorNotice message={error} onRetry={file ? () => void runPreview() : undefined} />
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={() => void runPreview()} disabled={!file || previewing}>
                {previewing ? "Checking…" : "Check file"}
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="grid gap-5">
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Import summary">
              {(
                [
                  ["Ready to save", preview.valid],
                  ["Already leads", preview.duplicate_existing],
                  ["Repeated in file", preview.duplicate_in_file],
                  ["Needs fixing", preview.invalid],
                ] as const
              ).map(([label, value]) => (
                <div key={label} className="rounded-lg border border-border bg-card p-3">
                  <dt className="text-sm text-muted-foreground">{label}</dt>
                  <dd className="mt-1 text-2xl font-semibold">{value}</dd>
                </div>
              ))}
            </dl>

            <p className="text-sm text-muted-foreground">
              {preview.file_name} · {preview.total_rows} {preview.total_rows === 1 ? "row" : "rows"}
              . Only the {preview.valid} ready {preview.valid === 1 ? "row" : "rows"} will be saved.
            </p>

            {preview.warnings.map((warning) => (
              <Notice key={warning} kind="error">
                {warning}
              </Notice>
            ))}

            <div className="grid gap-1 text-sm">
              <p className="font-medium">Column matching</p>
              <ul className="flex flex-wrap gap-2" aria-label="Column matching">
                {preview.columns.map((col, index) => (
                  <li key={`${col.column}-${index}`}>
                    <Badge variant="outline" className="max-w-full break-all font-normal">
                      {col.column || "(blank heading)"}
                      {" → "}
                      {col.field ?? "ignored"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </div>

            <div className="grid gap-2">
              <div className="max-h-72 overflow-auto rounded-md border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">Row</TableHead>
                      <TableHead className="w-32">Status</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Note</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.rows.slice(0, PREVIEW_ROW_LIMIT).map((row) => (
                      <TableRow key={row.row_number}>
                        <TableCell>{row.row_number}</TableCell>
                        <TableCell>
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASS[row.status]}`}
                          >
                            {STATUS_LABEL[row.status]}
                          </span>
                        </TableCell>
                        <TableCell className="min-w-0 break-words">
                          {[row.name, row.email, row.phone].filter(Boolean).join(" · ") ||
                            "No contact details"}
                        </TableCell>
                        <TableCell className="break-words text-muted-foreground">
                          {row.reason ?? (row.consent ? `Consent: ${row.consent}` : "")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {preview.rows.length > PREVIEW_ROW_LIMIT && (
                <p className="text-sm text-muted-foreground">
                  Showing the first {PREVIEW_ROW_LIMIT} of {preview.rows.length} rows. Every ready
                  row is included when you save.
                </p>
              )}
            </div>

            {error && <ErrorNotice message={error} />}

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setPreview(null);
                  setError("");
                }}
                disabled={saving}
              >
                Choose another file
              </Button>
              <Button onClick={() => void confirmSave()} disabled={saving || preview.valid === 0}>
                {saving
                  ? "Saving…"
                  : `Save ${preview.valid} ${preview.valid === 1 ? "contact" : "contacts"}`}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
