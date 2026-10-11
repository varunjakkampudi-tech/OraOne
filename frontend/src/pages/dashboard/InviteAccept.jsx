import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2, CheckCircle2, XCircle, Users } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * InviteAccept — Phase 12 Module 3.
 *
 * Landing page for `/app/invite/:token`. Previews the invitation, then lets
 * the signed-in (and email-matching) user accept it to join the org.
 */
export default function InviteAccept() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, identity } = useAuth();
  const myEmail = identity?.user?.email || user?.email || null;

  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState(null);
  const [accepting, setAccepting] = useState(false);
  const [done, setDone] = useState(null);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/team/invite/preview", { params: { token } });
      setPreview(data);
    } catch (e) {
      setPreview({ valid: false, reason: formatApiError(e) });
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  const accept = async () => {
    setAccepting(true);
    try {
      const { data } = await api.post("/team/invite/accept", { token });
      setDone(data);
      toast.success(data.message || "You've joined the team.");
      setTimeout(() => navigate("/app/dashboard"), 1500);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setAccepting(false);
    }
  };

  const emailMismatch =
    preview?.valid &&
    myEmail &&
    preview.email &&
    myEmail.toLowerCase() !== preview.email.toLowerCase();

  return (
    <div className="min-h-screen grid place-items-center bg-[#F8FAFC] px-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-white rounded-2xl border border-[#E2E8F0] shadow-xl p-8 text-center"
      >
        <div className="w-14 h-14 rounded-2xl bg-[#EFF6FF] grid place-items-center mx-auto">
          <Users className="w-7 h-7 text-[#2563EB]" />
        </div>

        {loading ? (
          <div className="py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[#2563EB] mx-auto" />
          </div>
        ) : done ? (
          <>
            <CheckCircle2 className="w-10 h-10 text-[#16A34A] mx-auto mt-4" />
            <h1 className="text-xl font-bold text-[#0F172A] mt-3">Welcome aboard!</h1>
            <p className="text-[#64748B] mt-1">{done.message}</p>
            <p className="text-sm text-[#94A3B8] mt-4">Redirecting to your dashboard…</p>
          </>
        ) : preview?.valid ? (
          <>
            <h1 className="text-xl font-bold text-[#0F172A] mt-4">
              Join {preview.organization_name}
            </h1>
            <p className="text-[#64748B] mt-1">
              You've been invited as <span className="font-semibold capitalize">{preview.role}</span>.
            </p>
            <div className="mt-2 text-sm text-[#64748B]">
              Invitation for <span className="font-medium">{preview.email}</span>
            </div>

            {emailMismatch && (
              <div className="mt-4 text-sm text-[#B45309] bg-[#FEF3C7] rounded-lg px-3 py-2">
                You're signed in as {myEmail}. Sign in with {preview.email} to accept this invite.
              </div>
            )}

            <button
              onClick={accept}
              disabled={accepting || emailMismatch}
              className="mt-6 w-full py-2.5 rounded-xl bg-[#2563EB] text-white font-medium hover:bg-[#1D4ED8] disabled:opacity-50 inline-flex items-center justify-center gap-2"
            >
              {accepting && <Loader2 className="w-4 h-4 animate-spin" />}
              Accept invitation
            </button>
          </>
        ) : (
          <>
            <XCircle className="w-10 h-10 text-[#DC2626] mx-auto mt-4" />
            <h1 className="text-xl font-bold text-[#0F172A] mt-3">Invitation unavailable</h1>
            <p className="text-[#64748B] mt-1">
              {preview?.reason || "This invitation link is no longer valid."}
            </p>
            <button
              onClick={() => navigate("/app/dashboard")}
              className="mt-6 w-full py-2.5 rounded-xl border border-[#E2E8F0] text-[#0F172A] font-medium hover:bg-[#F8FAFC]"
            >
              Go to dashboard
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
}
