import { AlertTriangle, CheckCircle2, Clock3, Inbox, Loader2 } from "lucide-react";

// All visual values come from tailwind.config.js tokens. Nothing here names a
// raw hex, so a palette change is a one-file edit.
// ponytail: single variant map instead of a cva dependency; add a variant
// library only if this table outgrows ~3 variants per component.

const FOCUS = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-container focus-visible:ring-offset-1";

const VARIANTS = {
  primary: "bg-primary-container text-on-primary shadow-card hover:bg-primary",
  secondary: "bg-surface-lowest text-on-surface border border-outline-variant hover:bg-surface-low",
  ghost: "text-on-surface-variant hover:bg-surface-low hover:text-on-surface",
  danger: "bg-danger text-on-primary shadow-card hover:bg-danger-ink",
};

const SIZES = {
  sm: "h-8 px-3 text-xs",
  md: "h-9 px-3.5 text-sm",
  lg: "h-11 px-5 text-sm",
};

export function Button({ variant = "primary", size = "md", className = "", as: Tag = "button", ...props }) {
  return (
    <Tag
      className={`inline-flex shrink-0 items-center justify-center gap-1.5 rounded font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 ${FOCUS} ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    />
  );
}

export function IconButton({ label, className = "", children, ...props }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex size-9 items-center justify-center rounded text-on-surface-variant transition-colors hover:bg-surface-low hover:text-on-surface ${FOCUS} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Card({ className = "", children, ...props }) {
  return (
    <div className={`rounded-lg border border-outline-variant bg-surface-lowest shadow-card ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ title, description, actions, icon: Icon, className = "" }) {
  return (
    <div className={`flex flex-wrap items-start justify-between gap-3 border-b border-outline-variant px-4 py-3 ${className}`}>
      <div className="flex min-w-0 items-start gap-2.5">
        {Icon && (
          <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded border border-outline-variant bg-surface-low text-on-surface-variant">
            <Icon className="size-4" />
          </span>
        )}
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-on-surface">{title}</h2>
          {description && <p className="mt-0.5 text-xs leading-relaxed text-on-surface-variant">{description}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

const TONES = {
  high: "text-danger-ink bg-danger-soft border-danger-line",
  moderate: "text-warning-ink bg-warning-soft border-warning-line",
  low: "text-success-ink bg-success-soft border-success-line",
  neutral: "text-on-surface-variant bg-surface-low border-outline-variant",
  primary: "text-primary bg-primary-soft border-primary-line",
};

const DOTS = {
  high: "bg-danger",
  moderate: "bg-warning",
  low: "bg-success",
  neutral: "bg-outline",
  primary: "bg-primary-container",
};

export function Badge({ tone = "neutral", dot = false, className = "", children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {dot && <span className={`size-1.5 shrink-0 rounded-full ${DOTS[tone]}`} aria-hidden="true" />}
      {children}
    </span>
  );
}

export function ResultBadge({ prediction }) {
  if (prediction === null || prediction === undefined) {
    return <Badge tone="neutral">Pending</Badge>;
  }
  return (
    <Badge tone={prediction === 1 ? "high" : "low"} dot>
      {prediction === 1 ? "CKD indicated" : "No CKD indicated"}
    </Badge>
  );
}

export function StatCard({ label, value, unit, hint, tone = "neutral", icon: Icon }) {
  const valueTone =
    tone === "high" ? "text-danger-ink" : tone === "moderate" ? "text-warning-ink" : tone === "low" ? "text-success-ink" : "text-on-surface";
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-on-surface-variant">{label}</p>
        {Icon && <Icon className="size-4 shrink-0 text-outline" aria-hidden="true" />}
      </div>
      <div className="mt-1.5 flex items-baseline gap-1">
        <span className={`tabular text-2xl font-semibold leading-none tracking-tight ${valueTone}`}>{value}</span>
        {unit && <span className="text-xs text-on-surface-variant">{unit}</span>}
      </div>
      {hint && <p className="mt-1.5 text-xs leading-relaxed text-on-surface-variant">{hint}</p>}
    </Card>
  );
}

export function ProgressBar({ value, tone = "primary", showCutoff = null, className = "" }) {
  const pct = Math.max(0, Math.min(1, Number(value) || 0)) * 100;
  const fill =
    tone === "high" ? "bg-danger" : tone === "moderate" ? "bg-warning" : tone === "low" ? "bg-success" : "bg-primary-container";
  return (
    <div className={`relative h-2 w-full overflow-hidden rounded-full bg-surface-container ${className}`}>
      <div className={`h-full rounded-full transition-[width] duration-500 ${fill}`} style={{ width: `${pct}%` }} />
      {showCutoff !== null && (
        <span
          className="absolute inset-y-0 w-0.5 bg-on-surface/70"
          style={{ left: `${Math.max(0, Math.min(1, showCutoff)) * 100}%` }}
          title={`Decision threshold ${showCutoff}`}
        />
      )}
    </div>
  );
}

export const inputClass =
  "w-full h-9 rounded border border-outline-variant bg-surface-lowest px-3 text-sm text-on-surface placeholder:text-outline transition-colors hover:border-outline focus:border-primary-container focus:outline-none focus:ring-[3px] focus:ring-primary-soft disabled:cursor-not-allowed disabled:bg-surface-low disabled:text-on-surface-variant";

export function Input({ className = "", ...props }) {
  return <input className={`${inputClass} tabular ${className}`} {...props} />;
}

export function Select({ className = "", children, ...props }) {
  return (
    <select className={`${inputClass} cursor-pointer appearance-none bg-[length:14px] bg-[right_0.6rem_center] bg-no-repeat pr-8 ${className}`} {...props}>
      {children}
    </select>
  );
}

export function Textarea({ className = "", ...props }) {
  return <textarea className={`${inputClass} h-auto min-h-20 py-2 leading-relaxed ${className}`} {...props} />;
}

export function Field({ label, hint, error, htmlFor, required, children }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 flex items-center gap-1 text-xs font-medium text-on-surface">
        {label}
        {required && <span className="text-danger">*</span>}
        {hint && !error && <span className="font-normal text-on-surface-variant">— {hint}</span>}
      </label>
      {children}
      {error && (
        <p className="mt-1 flex items-start gap-1 text-xs leading-relaxed text-danger-ink">
          <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}

/* ---- data table ------------------------------------------------------- */

export function Table({ children, minWidth = 640, className = "" }) {
  return (
    <div className="scrollbar-slim overflow-x-auto">
      <table className={`w-full text-left text-sm ${className}`} style={{ minWidth }}>
        {children}
      </table>
    </div>
  );
}

export function THead({ children }) {
  return (
    <thead className="border-b border-outline-variant bg-surface-low text-xs font-medium text-on-surface-variant">
      {children}
    </thead>
  );
}

export function TH({ children, className = "" }) {
  return <th className={`whitespace-nowrap px-3 py-2 text-left font-medium ${className}`}>{children}</th>;
}

export function TBody({ children }) {
  return <tbody className="divide-y divide-outline-variant">{children}</tbody>;
}

export function TD({ children, className = "" }) {
  return <td className={`px-3 py-2.5 align-middle text-sm text-on-surface ${className}`}>{children}</td>;
}

/* ---- states ----------------------------------------------------------- */

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded bg-surface-container ${className}`} />;
}

export function Spinner({ className = "" }) {
  return <Loader2 className={`size-4 animate-spin ${className}`} aria-hidden="true" />;
}

export function Alert({ tone = "danger", title, children, action }) {
  const styles =
    tone === "danger"
      ? "bg-danger-soft border-danger-line text-danger-ink"
      : tone === "warning"
        ? "bg-warning-soft border-warning-line text-warning-ink"
        : "bg-primary-soft border-primary-line text-primary";
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={`flex items-start gap-2 rounded border p-3 text-xs ${styles}`}>
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        <p className="leading-relaxed">{children}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, body, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-full border border-outline-variant bg-surface-low text-outline">
        <Icon className="size-5" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-on-surface">{title}</h3>
      <p className="mt-1 max-w-sm text-xs leading-relaxed text-on-surface-variant">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", body, onRetry, retryLabel = "Try again" }) {
  return (
    <EmptyState
      icon={AlertTriangle}
      title={title}
      body={body}
      action={
        onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        )
      }
    />
  );
}

export function StatusPill({ status }) {
  if (status === "verified") {
    return (
      <Badge tone="low">
        <CheckCircle2 className="size-3" aria-hidden="true" /> Verified
      </Badge>
    );
  }
  return (
    <Badge tone="neutral">
      <Clock3 className="size-3" aria-hidden="true" /> Archived
    </Badge>
  );
}