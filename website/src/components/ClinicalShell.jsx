import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  BarChart3,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Stethoscope,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const NAV = {
  doctor: [
    { to: "/doctor-dashboard", label: "Roster", icon: Users },
    { to: "/models", label: "Models", icon: BarChart3 },
  ],
  patient: [
    { to: "/dashboard", label: "Assessment", icon: LayoutDashboard },
    { to: "/history", label: "History", icon: History },
    { to: "/models", label: "Models", icon: BarChart3 },
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

function NavItems({ items, onNavigate }) {
  return items.map(({ to, label, icon: Icon }) => (
    <NavLink
      key={to}
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded px-2.5 py-2 text-[13px] font-medium transition-colors ${
          isActive
            ? "bg-primary-soft text-primary"
            : "text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
        }`
      }
    >
      <Icon className="size-4 shrink-0" />
      <span className="truncate">{label}</span>
    </NavLink>
  ));
}

export function ClinicalShell({ title, subtitle, actions, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const items = NAV[user?.role] ?? NAV.patient;
  const roleLabel = user?.role === "doctor" ? "Clinician" : "Patient";
  const initials = (user?.email ?? "??").slice(0, 2).toUpperCase();

  const signOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const sidebar = (onNavigate) => (
    <>
      <div className="flex h-14 items-center gap-2.5 border-b border-outline-variant px-4">
        <span className="flex size-8 items-center justify-center rounded bg-primary-container text-on-primary">
          <CorvusMark className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-bold leading-tight">Corvus</p>
          <p className="truncate text-[10px] uppercase tracking-wider text-on-surface-variant">
            CKD Platform
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        <p className="px-2.5 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-outline">
          Workspace
        </p>
        <NavItems items={items} onNavigate={onNavigate} />
      </nav>

      <div className="border-t border-outline-variant p-2">
        <div className="flex items-center gap-2 rounded px-2 py-1.5">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-container text-[10px] font-bold text-on-surface-variant">
            {initials}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold leading-tight">{user?.email}</p>
            <p className="text-[10px] uppercase tracking-wider text-on-surface-variant">{roleLabel}</p>
          </div>
        </div>
        <button
          onClick={signOut}
          className="mt-1 flex w-full items-center gap-2.5 rounded px-2.5 py-2 text-[13px] font-medium text-on-surface-variant transition-colors hover:bg-surface-low hover:text-on-surface"
        >
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-surface bg-kidney-pattern">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-outline-variant bg-surface-lowest/90 backdrop-blur-sm lg:flex">
        {sidebar(undefined)}
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-[#0b1c30]/45" onClick={() => setOpen(false)} />
          <aside className="relative flex h-full w-64 flex-col border-r border-outline-variant bg-surface-lowest/95 backdrop-blur-sm">
            <button
              onClick={() => setOpen(false)}
              className="absolute right-2 top-3.5 rounded p-1 text-on-surface-variant hover:bg-surface-low"
              aria-label="Close navigation"
            >
              <X className="size-4" />
            </button>
            {sidebar(() => setOpen(false))}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 items-center gap-3 border-b border-outline-variant bg-surface-lowest/90 backdrop-blur-sm px-4">
          <button
            onClick={() => setOpen(true)}
            className="rounded p-1.5 text-on-surface-variant hover:bg-surface-low lg:hidden"
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-bold leading-tight text-on-surface">{title}</h1>
            {subtitle && (
              <p className="truncate text-[11px] text-on-surface-variant">{subtitle}</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {actions}
            <span className="hidden items-center gap-1.5 rounded border border-outline-variant bg-surface-low px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-secondary sm:inline-flex">
              <Stethoscope className="size-3" />
              {roleLabel}
            </span>
          </div>
        </header>

        <main className="flex-1 overflow-x-hidden px-4 py-5 sm:px-6">{children}</main>
        <p className="border-t border-outline-variant px-4 py-2 text-[10px] leading-relaxed text-on-surface-variant sm:px-6">
          Screening aid only, not a diagnosis. High-recall/low-precision model, so a
          positive flag needs clinical confirmation.
        </p>
      </div>
    </div>
  );
}
