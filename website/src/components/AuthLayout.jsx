import { Link } from "react-router-dom";
import { Activity, BarChart3, Database, ShieldCheck } from "lucide-react";
import { CorvusMark } from "./ClinicalShell";

// Modern clinical metrics highlight cards based on Stitch UI designs
const CLINICAL_METRICS = [
  {
    label: "Cohort Volume",
    value: "15,244",
    detail: "NHANES Multi-Cycle Dataset",
    icon: Database,
  },
  {
    label: "Discrimination",
    value: "0.8214",
    detail: "Holdout ROC-AUC (v15 model)",
    icon: BarChart3,
  },
  {
    label: "Biomarker Depth",
    value: "23",
    detail: "Native lab & demographic features",
    icon: Activity,
  },
];

export function AuthLayout({ children }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-surface">
      {/* Background ambient lighting accents */}
      <div className="pointer-events-none fixed left-0 top-0 -translate-x-1/2 -translate-y-1/2 size-96 rounded-full bg-primary/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 translate-x-1/3 translate-y-1/3 size-[30rem] rounded-full bg-primary-container/10 blur-[140px]" />

      <header className="relative z-10 border-b border-outline-variant/60 bg-surface-lowest/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/login" className="flex items-center gap-2.5">
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-on-primary shadow-sm shadow-primary/20">
              <CorvusMark className="size-5" />
            </span>
            <span>
              <span className="flex items-center gap-2 text-sm font-bold tracking-tight text-on-surface">
                CORVUS <span className="font-medium text-primary">CLINICAL</span>
              </span>
              <span className="block text-xs text-on-surface-variant">CKD MLOps Platform · v15</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 rounded-full border border-success-line bg-success-soft px-2.5 py-0.5 text-xs font-medium text-success-ink sm:inline-flex">
              <span className="size-1.5 rounded-full bg-success animate-pulse" />
              API v2 Online
            </span>
            <span className="hidden items-center gap-1.5 text-xs font-medium text-on-surface-variant sm:inline-flex">
              <ShieldCheck className="size-4 text-primary" aria-hidden="true" />
              Self-hosted · PostgreSQL
            </span>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto grid w-full max-w-6xl flex-1 items-center gap-10 px-4 py-10 sm:px-6 lg:grid-cols-12 lg:gap-12">
        {/* Left Side: Brand & Hero Showcase */}
        <section className="hidden space-y-6 lg:col-span-6 lg:block">
          <div className="inline-flex items-center gap-2 rounded-md border border-primary-line bg-primary-soft px-3 py-1 text-xs font-semibold uppercase tracking-wider text-primary">
            <Activity className="size-3.5" />
            Clinical Decision Support
          </div>

          <h1 className="text-balance text-4xl font-extrabold leading-tight tracking-tight text-on-surface xl:text-5xl">
            AI-Powered <span className="text-primary">CKD Screening</span> Platform
          </h1>

          <p className="max-w-lg text-base leading-relaxed text-on-surface-variant">
            Risk stratification powered by machine learning trained on multi-cycle NHANES cohorts. Screen early kidney
            impairment from routine biochemistry panels before irreversible loss of function.
          </p>

          {/* Validation Metrics Grid from Stitch Design */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            {CLINICAL_METRICS.map(({ label, value, detail, icon: Icon }) => (
              <div
                key={label}
                className="rounded-xl border border-outline-variant bg-surface-lowest p-3.5 shadow-sm transition-all hover:border-primary/40 hover:shadow"
              >
                <div className="flex items-center justify-between text-on-surface-variant">
                  <span className="text-xs font-medium">{label}</span>
                  <Icon className="size-3.5 text-primary" />
                </div>
                <div className="mt-1 text-xl font-bold tracking-tight text-on-surface">{value}</div>
                <p className="mt-1 text-xs leading-snug text-on-surface-variant">{detail}</p>
              </div>
            ))}
          </div>

          {/* Compliance & Standards Pill Bar */}
          <div className="flex items-center gap-4 border-t border-outline-variant pt-4 text-xs text-on-surface-variant">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-primary" />
              KDIGO Screening Protocol
            </span>
            <span>•</span>
            <span>Gradient Boosting Classifier</span>
            <span>•</span>
            <span>Zero-Leakage Cohort</span>
          </div>

          <p className="max-w-lg text-xs leading-relaxed text-on-surface-variant">
            *Screening aid only. Positive flags represent statistical risk indicators requiring clinical and lab confirmatory eGFR trajectory testing.
          </p>
        </section>

        {/* Right Side: Form Card */}
        <section className="w-full justify-self-center lg:col-span-6 lg:max-w-md">{children}</section>
      </main>

      <footer className="relative z-10 border-t border-outline-variant bg-surface-lowest/80 px-4 py-3 text-center text-xs text-on-surface-variant">
        Corvus Health · MLOps Clinical Decision Support · For authorized healthcare research and screening
      </footer>
    </div>
  );
}
