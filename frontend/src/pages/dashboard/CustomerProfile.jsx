import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Mail,
  MessageSquare,
  Phone,
  Save,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import {
  Badge,
  Card,
  PageHeader,
  PrimaryButton,
} from "@/components/dashboard/kit";
import { ErrorState, Skeleton } from "@/components/dashboard/states";

export default function CustomerProfile() {
  const { customerId } = useParams();
  const [customer, setCustomer] = useState(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get(
        "/leads/" + encodeURIComponent(customerId),
      );
      if (!data?.id || String(data.id) !== String(customerId)) {
        throw new Error(
          "Customer response does not match the requested record.",
        );
      }
      setCustomer(data);
      setNotes(data.notes || "");
    } catch (failure) {
      setCustomer(null);
      setError(
        formatApiError(failure.response?.data?.detail) ||
          "This customer is unavailable in the active workspace.",
      );
    } finally {
      setLoading(false);
    }
  }, [customerId]);
  useEffect(() => {
    load();
  }, [load]);
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(
        "/leads/" + encodeURIComponent(customerId),
        { notes },
      );
      setCustomer(data);
      setNotes(data.notes || "");
      toast.success("Customer notes saved");
    } catch (failure) {
      toast.error(
        formatApiError(failure.response?.data?.detail) ||
          "Notes could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="space-y-6">
      <Link
        to="/app/customers"
        className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-sub hover:text-brand"
      >
        <ArrowLeft size={16} />
        Customers &amp; leads
      </Link>
      <PageHeader
        title="Customer profile"
        subtitle="Contact details and conversation context from your workspace."
      />
      {loading ? (
        <div role="status" aria-busy="true">
          <Skeleton className="h-24" />
          <Skeleton className="mt-5 h-64" />
        </div>
      ) : error ? (
        <ErrorState
          title="Customer unavailable"
          message={error}
          onRetry={load}
        />
      ) : (
        customer && (
          <>
            <Card className="flex flex-wrap items-center gap-4 p-6">
              <span className="grid size-14 place-items-center rounded-full bg-brand-soft text-brand">
                <UserRound size={28} />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="break-words text-xl font-semibold text-ink">
                  {customer.name || "Unnamed contact"}
                </h2>
                <p className="mt-1 break-all text-sm text-sub">
                  {customer.email || "Email not provided"}
                </p>
              </div>
              <Badge
                tone={
                  customer.status === "Qualified" || customer.status === "Won"
                    ? "green"
                    : "slate"
                }
              >
                {customer.status}
              </Badge>
            </Card>
            <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
              <Card className="p-6">
                <h2 className="text-lg font-semibold text-ink">
                  Customer overview
                </h2>
                <dl className="mt-5 grid gap-5 sm:grid-cols-2">
                  {[
                    [Building2, "Company", customer.company],
                    [Mail, "Email", customer.email],
                    [Phone, "Phone", customer.phone],
                    [MessageSquare, "Source", customer.source],
                  ].map(([Icon, label, value]) => (
                    <div key={label}>
                      <dt className="flex items-center gap-2 text-sm text-sub">
                        <Icon size={15} />
                        {label}
                      </dt>
                      <dd className="mt-2 break-words text-sm font-medium text-ink">
                        {value || "Not provided"}
                      </dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-7 border-t border-hairline pt-5">
                  <h3 className="text-base font-semibold text-ink">
                    Conversation history
                  </h3>
                  {customer.conversation_id ? (
                    <Link
                      to={"/app/inbox/" + customer.conversation_id}
                      className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg border border-line px-4 text-sm font-semibold text-ink hover:bg-canvas"
                    >
                      View conversation <ArrowRight size={16} />
                    </Link>
                  ) : (
                    <p className="mt-2 text-sm text-sub">
                      No conversation is linked to this contact.
                    </p>
                  )}
                </div>
              </Card>
              <Card className="p-5">
                <label
                  htmlFor="customer-notes"
                  className="text-base font-semibold text-ink"
                >
                  Customer notes
                </label>
                <textarea
                  id="customer-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={6}
                  maxLength={4000}
                  className="mt-4 w-full rounded-lg border border-line bg-white p-3 text-sm leading-relaxed outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
                  placeholder="Add context for your team…"
                />
                <PrimaryButton
                  onClick={save}
                  disabled={saving || notes === (customer.notes || "")}
                  className="mt-4"
                >
                  <Save size={15} />
                  {saving ? "Saving…" : "Save notes"}
                </PrimaryButton>
              </Card>
            </div>
          </>
        )
      )}
    </div>
  );
}
