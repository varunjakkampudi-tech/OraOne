import React, { useRef } from "react";
import { Eye, EyeOff, Check } from "lucide-react";

/* ─────────────────────────────────────────────────────────── */
/* Field — label + optional trailing hint/link, wraps an input  */
/* ─────────────────────────────────────────────────────────── */
export function Field({ label, trailing, children }) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-sm font-medium text-[#0F172A]">{label}</span>
        {trailing}
      </div>
      {children}
    </label>
  );
}

export const inputCls =
  "w-full rounded-xl border border-[#E2E8F0] bg-white px-4 py-3 text-sm text-[#0F172A] placeholder:text-[#94A3B8] transition-all focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10";

const inputWithIconCls =
  "w-full rounded-xl border border-[#E2E8F0] bg-white py-3 pl-11 pr-4 text-sm text-[#0F172A] placeholder:text-[#94A3B8] transition-all focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10";

/* ─────────────────────────────────────────────────────────── */
/* IconInput — input with a leading lucide icon                 */
/* ─────────────────────────────────────────────────────────── */
export function IconInput({ icon: Icon, ...props }) {
  return (
    <div className="relative">
      {Icon && <Icon size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8]" />}
      <input {...props} className={Icon ? inputWithIconCls : inputCls} />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* PasswordInput — input with leading icon + show/hide toggle   */
/* ─────────────────────────────────────────────────────────── */
export function PasswordInput({ icon: Icon, "data-testid": testId, ...props }) {
  const [show, setShow] = React.useState(false);
  return (
    <div className="relative">
      {Icon && <Icon size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8]" />}
      <input
        {...props}
        type={show ? "text" : "password"}
        data-testid={testId}
        className={`w-full rounded-xl border border-[#E2E8F0] bg-white py-3 ${Icon ? "pl-11" : "pl-4"} pr-11 text-sm text-[#0F172A] placeholder:text-[#94A3B8] transition-all focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10`}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "Hide password" : "Show password"}
        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8] transition-colors hover:text-[#475569]"
      >
        {show ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* Password strength rules + live checklist                     */
/* ─────────────────────────────────────────────────────────── */
export const PASSWORD_RULES = [
  { id: "len", label: "8+ characters", test: (v) => v.length >= 8 },
  { id: "upper", label: "1 uppercase", test: (v) => /[A-Z]/.test(v) },
  { id: "num", label: "1 number", test: (v) => /\d/.test(v) },
  { id: "special", label: "1 special character", test: (v) => /[^A-Za-z0-9]/.test(v) },
];

export function passwordValid(value) {
  return PASSWORD_RULES.every((r) => r.test(value || ""));
}

/* Inline horizontal rule row (matches design — 4 chips in a row) */
export function PasswordRulesInline({ value = "" }) {
  return (
    <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1.5" aria-live="polite">
      {PASSWORD_RULES.map((rule) => {
        const ok = rule.test(value);
        return (
          <span key={rule.id} className="inline-flex items-center gap-1.5 text-xs">
            <span
              className={`grid size-4 place-items-center rounded-full transition-colors ${
                ok ? "bg-[#16A34A] text-white" : "bg-[#E2E8F0] text-transparent"
              }`}
            >
              <Check size={11} strokeWidth={3} />
            </span>
            <span className={ok ? "text-[#16A34A]" : "text-[#64748B]"}>{rule.label}</span>
          </span>
        );
      })}
    </div>
  );
}

export function PasswordChecklist({ value = "" }) {
  return (
    <ul className="mt-2.5 space-y-1.5" aria-live="polite">
      {PASSWORD_RULES.map((rule) => {
        const ok = rule.test(value);
        return (
          <li key={rule.id} className="flex items-center gap-2 text-xs">
            <span
              className={`grid size-4 place-items-center rounded-full transition-colors ${
                ok ? "bg-[#16A34A] text-white" : "bg-[#E2E8F0] text-transparent"
              }`}
            >
              <Check size={11} strokeWidth={3} />
            </span>
            <span className={ok ? "text-[#16A34A]" : "text-[#64748B]"}>{rule.label}</span>
          </li>
        );
      })}
    </ul>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* Checkbox — custom styled, used for remember-me / terms       */
/* ─────────────────────────────────────────────────────────── */
export function Checkbox({ checked, onChange, children, id, accentClass, "data-testid": testId }) {
  const accent =
    accentClass ||
    "peer-checked:border-[#2563EB] peer-checked:bg-[#2563EB] peer-focus-visible:ring-[#2563EB]/15";
  return (
    <label htmlFor={id} className="flex cursor-pointer select-none items-start gap-2.5 text-sm text-[#64748B]">
      <span className="relative mt-0.5 inline-flex">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          data-testid={testId}
          className="peer sr-only"
        />
        <span className={`grid size-[18px] place-items-center rounded-md border border-[#CBD5E1] bg-white transition-all peer-focus-visible:ring-4 ${accent}`}>
          {checked && <Check size={12} strokeWidth={3} className="text-white" />}
        </span>
      </span>
      <span className="leading-snug">{children}</span>
    </label>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* OtpInput — 6 single-digit boxes with auto-advance + paste     */
/* ─────────────────────────────────────────────────────────── */
export function OtpInput({ value = "", onChange, length = 6, "data-testid": testId }) {
  const refs = useRef([]);
  const digits = Array.from({ length }, (_, i) => value[i] || "");

  const setDigit = (i, d) => {
    const next = value.split("");
    next[i] = d;
    onChange(next.join("").slice(0, length));
  };

  const handleChange = (i, raw) => {
    const d = raw.replace(/\D/g, "");
    if (!d) {
      setDigit(i, "");
      return;
    }
    // Take the last typed character
    setDigit(i, d[d.length - 1]);
    if (i < length - 1) refs.current[i + 1]?.focus();
  };

  const handleKeyDown = (i, e) => {
    if (e.key === "Backspace" && !digits[i] && i > 0) {
      refs.current[i - 1]?.focus();
    } else if (e.key === "ArrowLeft" && i > 0) {
      refs.current[i - 1]?.focus();
    } else if (e.key === "ArrowRight" && i < length - 1) {
      refs.current[i + 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, length);
    if (pasted) {
      onChange(pasted);
      refs.current[Math.min(pasted.length, length - 1)]?.focus();
    }
  };

  return (
    <div className="flex items-center justify-center gap-2 sm:gap-3" data-testid={testId}>
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => (refs.current[i] = el)}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          maxLength={1}
          value={d}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          aria-label={`Digit ${i + 1}`}
          className="size-12 rounded-xl border border-[#E2E8F0] bg-white text-center text-lg font-semibold text-[#0F172A] transition-all focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 sm:size-[52px]"
        />
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* InfoNote — soft blue informational callout                   */
/* ─────────────────────────────────────────────────────────── */
export function InfoNote({ icon: Icon, children }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-[#DBEAFE] bg-[#EFF6FF] p-4 text-left">
      {Icon && (
        <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-white text-[#2563EB] shadow-sm">
          <Icon size={16} />
        </span>
      )}
      <p className="text-xs leading-relaxed text-[#475569]">{children}</p>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* SubmitButton — primary full-width auth action                */
/* ─────────────────────────────────────────────────────────── */
export function SubmitButton({ children, ...props }) {
  return (
    <button
      {...props}
      className="w-full rounded-xl bg-[#2563EB] py-3 text-sm font-semibold text-white shadow-[0_2px_10px_rgba(37,99,235,0.2)] transition-all hover:bg-[#1D4ED8] hover:shadow-[0_4px_15px_rgba(37,99,235,0.3)] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}
