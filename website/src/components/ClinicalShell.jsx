import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Stethoscope,
  UserRound,
  UserRoundPlus,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "../contexts/authStore";
import { predictionAPI } from "../api";
import { IconButton } from "./ui";

const NAV = {
  doctor: [
    { to: "/doctor-dashboard", label: "Patient roster", icon: Users },
    { to: "/assign-patients", label: "Assign patients", icon: UserRoundPlus },
    { to: "/models", label: "Model performance", icon: BarChart3 },
    { to: "/doctor-profile", label: "Profile", icon: Stethoscope },
  ],
  patient: [
    { to: "/dashboard", label: "New assessment", icon: LayoutDashboard },
    { to: "/history", label: "Prediction history", icon: History },
    { to: "/models", label: "Model performance", icon: BarChart3 },
    { to: "/profile", label: "Profile", icon: UserRound },
  ],
};

export function CorvusMark({ className = "size-7" }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="currentColor" aria-hidden="true">
      <path d="M42.17 20.17 27.83 5.83c1.31 1.31.57 4.36-1.63 7.93a36 36 0 0 1-5.55 6.89 36 36 0 0 1-6.88 5.55c-3.58 2.2-6.63 2.94-7.94 1.63L20.17 42.17c1.31 1.31 4.36.57 7.94-1.63a36 36 0 0 0 6.89-5.55 36 36 0 0 0 5.54-6.88c2.2-3.58 2.94-6.63 1.63-7.94Z" />
      <path d="M7.24 26.4c1.03.44 3.44-.24 6.6-2.11a43 43 0 0 0 7.05-5.18 43 43 0 0 0 5.18-7.05c1.87-3.16 2.55-5.57 2.11-6.6l11.3 11.3c.44 1.04-.24 3.45-2.11 6.61a43 43 0 0 1-5.18 7.05 43 43 0 0 1-7.05 5.18c-3.16 1.87-5.57 2.55-6.6 2.11L7.24 26.4Z" opacity=".35" />
    </svg>
  );
}

// One health probe per page load, shared by every shell instance. A status
// light that is not real is worse than no status light.
let healthPromise = null;
function useApiHealth() {
  const [state, setState] = useState({ status: "loading", version: null });
  useEffect(() => {
    healthPromise ??= predictionAPI.health().then((r) => r.data, () => null);
    let alive = true;
    healthPromise.then((data) => {
      if (!alive) return;
      setState(data ? { status: "online", version: data.model_version_v2 ?? data.model_version } : { status: "offline", version: null });
    });
    return () => {
      alive = false;
    };
  }, []);
  return state;
}

function NavItems({ items, onNavigate }) {
  return items.map(({ to, label, icon: Icon }) => (
    <NavLink
      key={to}
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `group relative flex items-center gap-2.5 rounded px-2.5 py-2 text-sm transition-colors ${
          isActive
            ? "bg-primary-soft font-semibold text-primary"
            : "font-medium text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={`absolute inset-y-1 left-0 w-0.5 rounded-full bg-primary transition-opacity ${isActive ? "opacity-100" : "opacity-0"}`}
            aria-hidden="true"
          />
          <Icon className="size-4 shrink-0" aria-hidden="true" />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  ));
}

function HealthChip() {
  const { status, version } = useApiHealth();
  const tone =
    status === "online"
      ? "text-success-ink bg-success-soft border-success-line"
      : status === "offline"
        ? "text-danger-ink bg-danger-soft border-danger-line"
        : "text-on-surface-variant bg-surface-low border-outline-variant";
  const label = status === "online" ? `API online · v${version}` : status === "offline" ? "API unreachable" : "Checking API";
  return (
    <span className={`hidden items-center gap-1.5 rounded border px-2 py-1 text-xs font-medium md:inline-flex ${tone}`}>
      <Activity className="size-3" aria-hidden="true" />
      {label}
    </span>
  );
}

export function ClinicalShell({ title, subtitle, actions, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const items = NAV[user?.role] ?? NAV.patient;
  const roleLabel = user?.role === "doctor" ? "Clinician" : "Patient";
  const displayName = user?.profile?.full_name || user?.email || "Signed in";
  const initials = displayName.slice(0, 2).toUpperCase();

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  const signOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const sidebar = (onNavigate) => (
    <>
      <div className="flex h-16 items-center gap-2.5 border-b border-outline-variant px-4">
        <span className="flex size-9 items-center justify-center rounded bg-primary-container text-on-primary">
          <CorvusMark className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold leading-tight text-on-surface">Corvus Health</p>
          <p className="truncate text-xs leading-tight text-on-surface-variant">CKD risk platform</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        <p className="px-2.5 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-on-surface-variant">Workspace</p>
        <NavItems items={items} onNavigate={onNavigate} />
      </nav>

      <div className="border-t border-outline-variant p-2">
        <div className="flex items-center gap-2 rounded px-2 py-1.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-container text-xs font-semibold text-on-surface-variant">
            {initials}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold leading-tight text-on-surface">{displayName}</p>
            <p className="text-xs leading-tight text-on-surface-variant">{roleLabel}</p>
          </div>
        </div>
        <button
          onClick={signOut}
          className="mt-1 flex w-full items-center gap-2.5 rounded px-2.5 py-2 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-low hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-container"
        >
          <LogOut className="size-4" aria-hidden="true" />
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-surface">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-outline-variant bg-surface-lowest lg:flex">
        {sidebar(undefined)}
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-on-surface/40" onClick={() => setOpen(false)} aria-hidden="true" />
          <aside
            className="relative flex h-full w-72 max-w-[85vw] flex-col border-r border-outline-variant bg-surface-lowest shadow-pop"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
          >
            <IconButton label="Close navigation" className="absolute right-2 top-3.5 z-10" onClick={() => setOpen(false)}>
              <X className="size-4" />
            </IconButton>
            {sidebar(() => setOpen(false))}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex min-h-16 flex-wrap items-center gap-3 border-b border-outline-variant bg-surface-lowest/95 px-4 py-2 backdrop-blur sm:px-6">
          <IconButton label="Open navigation" className="lg:hidden" onClick={() => setOpen(true)}>
            <Menu className="size-5" />
          </IconButton>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-semibold leading-tight text-on-surface">{title}</h1>
            {subtitle && <p className="truncate text-xs leading-tight text-on-surface-variant">{subtitle}</p>}
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <HealthChip />
            {actions}
          </div>
        </header>

        <main className="flex-1 overflow-x-hidden px-4 py-6 sm:px-6">{children}</main>
        <p className="border-t border-outline-variant px-4 py-2.5 text-xs leading-relaxed text-on-surface-variant sm:px-6">
          Screening aid only, not a diagnosis. The model is tuned for high recall at low precision, so a positive flag needs
          clinical confirmation.
        </p>
      </div>
    </div>
  );
}
