import { AlertTriangle, CheckCircle2, Clock3, Inbox, Loader2 } from "lucide-react";

const VARIANTS = {
  primary: "bg-primary-container text-on-primary hover:bg-primary",
  secondary: "bg-surface-lowest text-on-surface border border-outline-variant hover:bg-surface-low",
  ghost: "text-on-surface-variant hover:bg-surface-low",
  danger: "bg-error text-white hover:bg-[#981414]",
};

const SIZES = {
  sm: "h-7 px-2.5 text-[11px]",
  md: "h-8 px-3 text-xs",
  lg: "h-10 px-4 text-sm",
};

export function Button({ variant = "primary", size = "md", className = "", as: Tag = "button", ...props }) {
  return (
    <Tag
      className={`inline-flex items-center justify-center gap-1.5 rounded font-semibold transition-colors disabled:opacity-50 disabled:pointer-events-none ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    />
  );
}

export function Card({ className = "", children }) {
  return <div className={`rounded-lg border border-outline-variant bg-surface-lowest ${className}`}>{children}</div>;
}

const TONES = {
  high: "text-[#991B1B] bg-[#FEF2F2] border-[#FECACA]",
  moderate: "text-[#92400E] bg-[#FFFBEB] border-[#FDE68A]",
  low: "text-[#065F46] bg-[#ECFDF5] border-[#A7F3D0]",
  neutral: "text-[#334155] bg-surface-low border-[#CBD5E1]",
  primary: "text-primary bg-primary-soft border-[#b8c4ff]",
};

const DOTS = {
  high: "bg-[#DC2626]",
  moderate: "bg-[#D97706]",
  low: "bg-[#059669]",
  neutral: "bg-[#64748B]",
  primary: "bg-primary-container",
};

export function Badge({ tone = "neutral", dot = true, className = "", children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${TONES[tone]} ${className}`}
    >
      {dot && <span className={`size-1.5 rounded-full ${DOTS[tone]}`} />}
      {children}
    </span>
  );
}

export function ResultBadge({ prediction }) {
  return (
    <Badge tone={prediction === 1 ? "high" : "low"}>
      {prediction === 1 ? "CKD Detected" : "No CKD Detected"}
    </Badge>
  );
}

export function StatCard({ label, value, hint, tone = "neutral" }) {
  return (
    <Card className="min-w-[158px] flex-1 p-4">
      <p className="text-xs font-medium text-on-surface">{label}</p>
      <p className={`mt-1 text-2xl font-bold leading-tight tabular ${tone === "high" ? "text-tertiary" : "text-on-surface"}`}>
        {value}
      </p>
      {hint && <p className="mt-0.5 text-[11px] text-on-surface-variant">{hint}</p>}
    </Card>
  );
}

export const inputClass =
  "w-full h-8 rounded border border-outline-variant bg-surface-lowest px-2.5 text-sm text-on-surface placeholder:text-[#8a8f9e] focus:border-primary-container focus:outline-none focus:ring-1 focus:ring-primary-container disabled:bg-surface-low disabled:text-on-surface-variant";

export function Input({ className = "", ...props }) {
  return <input className={`${inputClass} tabular ${className}`} {...props} />;
}

export function Select({ className = "", children, ...props }) {
  return (
    <select className={`${inputClass} appearance-none pr-7 ${className}`} {...props}>
      {children}
    </select>
  );
}

export function Field({ label, hint, htmlFor, children }) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-on-surface"
      >
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-[11px] leading-tight text-on-surface-variant">{hint}</p>}
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded bg-surface-container ${className}`} />;
}

export function Spinner({ className = "" }) {
  return <Loader2 className={`size-4 animate-spin ${className}`} />;
}

export function Alert({ tone = "error", title, children }) {
  const styles =
    tone === "error"
      ? "bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]"
      : "bg-[#FFFBEB] border-[#FDE68A] text-[#92400E]";
  return (
    <div className={`flex items-start gap-2 rounded border p-3 text-xs ${styles}`}>
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <div>
        {title && <p className="font-bold">{title}</p>}
        <p className="leading-relaxed">{children}</p>
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, body, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex size-14 items-center justify-center rounded-full bg-surface-container text-outline">
        <Icon className="size-6" />
      </div>
      <h3 className="text-base font-bold text-on-surface">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-on-surface-variant">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function StatusPill({ status }) {
  if (status === "verified") {
    return (
      <Badge tone="low" className="normal-case">
        <CheckCircle2 className="size-3" /> Verified
      </Badge>
    );
  }
  return (
    <Badge tone="neutral" className="normal-case">
      <Clock3 className="size-3" /> Archived
    </Badge>
  );
}

export const fmtProbability = (p) => `${Number(p).toFixed(3)} (${(Number(p) * 100).toFixed(1)}%)`;
