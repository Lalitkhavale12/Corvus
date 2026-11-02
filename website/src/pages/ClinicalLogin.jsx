import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Database,
  Lock,
  ShieldCheck,
  Stethoscope,
  UserRound,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { authAPI } from "../api";
import { CorvusMark } from "../components/ClinicalShell";
import { Button, Card, Field, Input, Spinner } from "../components/ui";

export function ClinicalLogin() {
  const [role, setRole] = useState("doctor");
  const [email, setEmail] = useState("dr.jenkins@corvushealth.org");
  const [password, setPassword] = useState("ClinicalSec!2024");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const select = (r) => {
    setRole(r);
    setError("");
    if (r === "doctor") {
      if (email.includes("patient")) setEmail("dr.jenkins@corvushealth.org");
    } else if (email.includes("dr.jenkins")) {
      setEmail("maria.gonzalez@patient.corvushealth.org");
    }
  };

  const demo = (r, e) => {
    select(r);
    setEmail(e);
    setPassword(r === "doctor" ? "ClinicalSec!2024" : "HealthTrack$99");
  };

  const handle = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authAPI.login({ email, password });
      await login(res.data.access_token);
      navigate(role === "doctor" ? "/doctor-dashboard" : "/dashboard", { replace: true });
    } catch {
      setError("Invalid credentials for the selected portal.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-ckd-soft-gradient bg-nephron-pattern">
      <header className="border-b border-outline-variant bg-surface-lowest/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded bg-primary-container text-on-primary">
              <CorvusMark className="size-5" />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-primary">Corvus Health</p>
              <p className="text-[10px] font-mono uppercase tracking-wider text-on-surface-variant">
                CKD Engine v2.4-clinical
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-2 sm:flex">
            <span className="kidney-badge">
              <span className="size-3.5 text-secondary">🫀</span>
              CKD Console
            </span>
            <span className="flex items-center gap-1.5 rounded border border-outline-variant px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-secondary">
              <ShieldCheck className="size-3" /> Postgres Enclave Active
            </span>
            <a className="rounded border border-outline-variant px-2.5 py-1 text-[11px] font-medium text-on-surface-variant hover:bg-surface-low hover:text-on-surface">
              IT Helpdesk
            </a>
          </div>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-[480px]">
          <Card className="overflow-hidden shadow-sm">
            <div className="border-b border-outline-variant px-6 py-7 text-center sm:px-8">
              <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-lg border border-outline-variant bg-surface-low">
                <CorvusMark className="size-8" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-on-surface sm:text-2xl">
                Corvus CKD Risk Platform
              </h1>
              <p className="mt-1 text-sm text-on-surface-variant">
                Clinical Console &amp; Patient Health Portal
              </p>
              <div className="mt-4 inline-flex items-center gap-1.5 rounded border border-outline-variant bg-surface-low px-3 py-1.5 text-[11px] text-on-surface-variant">
                <Lock className="size-3.5 text-secondary" />
                Local Docker Compose • PostgreSQL secure enclave
              </div>

              <div className="mt-6 grid grid-cols-2 gap-1 rounded border border-outline-variant bg-surface-low p-1">
                <button
                  onClick={() => select("doctor")}
                  className={`flex items-center justify-center gap-1.5 rounded py-1.5 text-xs font-semibold transition-colors ${
                    role === "doctor"
                      ? "bg-surface-lowest text-primary shadow-sm"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  <Stethoscope className="size-3.5" /> Doctor / Clinician
                </button>
                <button
                  onClick={() => select("patient")}
                  className={`flex items-center justify-center gap-1.5 rounded py-1.5 text-xs font-semibold transition-colors ${
                    role === "patient"
                      ? "bg-surface-lowest text-primary shadow-sm"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  <UserRound className="size-3.5" /> Patient Portal
                </button>
              </div>
              <p className="mt-2.5 text-center text-xs leading-relaxed text-on-surface-variant">
                {role === "doctor"
                  ? "Sign in to access the patient roster, triage predictions, and run /v2/predict."
                  : "Sign in to submit NHANES vitals/labs and track your predictions."}
              </p>
            </div>

            <form onSubmit={handle} className="space-y-4 px-6 py-6 sm:px-8">
              <Field label="Email Address" htmlFor="email">
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>

              <Field label="Password" htmlFor="password">
                <div className="relative">
                  <Input
                    id="password"
                    type={show ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    className="pr-9 tabular"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((s) => !s)}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-1 text-on-surface-variant hover:bg-surface-low"
                    aria-label={show ? "Hide password" : "Show password"}
                  >
                    {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
              </Field>

              {error && (
                <div className="rounded border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#991B1B]">
                  {error}
                </div>
              )}

              <Button type="submit" size="lg" className="w-full" disabled={loading}>
                {loading ? <Spinner /> : <ArrowRight className="size-4" />}
                {loading
                  ? "Authenticating…"
                  : role === "doctor"
                  ? "Sign In to Clinical Console"
                  : "Sign In to Patient Portal"}
              </Button>

              <p className="text-center text-xs text-on-surface-variant">
                Need an account?{" "}
                <Link to="/register" className="font-medium text-primary hover:underline">
                  Register
                </Link>
              </p>
            </form>

            <div className="border-t border-outline-variant bg-surface-low px-6 py-4 sm:px-8">
              <div className="flex items-start gap-2">
                <Database className="mt-0.5 size-4 text-secondary" />
                <div className="min-w-0">
                  <p className="text-[11px] font-mono text-on-surface">
                    Docker Compose • /v2/predict • /v2/model_info • PostgreSQL 16
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="text-on-surface-variant">Demo:</span>
                    <button
                      onClick={() => demo("doctor", "dr.jenkins@corvushealth.org")}
                      className="rounded border border-outline-variant bg-surface-lowest px-2 py-0.5 font-mono text-primary hover:bg-surface-low"
                    >
                      doctor@corvushealth.org
                    </button>
                    <button
                      onClick={() => demo("patient", "maria.gonzalez@patient.corvushealth.org")}
                      className="rounded border border-outline-variant bg-surface-lowest px-2 py-0.5 font-mono text-primary hover:bg-surface-low"
                    >
                      patient@corvushealth.org
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </main>

      <footer className="border-t border-outline-variant bg-surface-lowest px-4 py-3 text-center text-[11px] text-on-surface-variant">
        © 2026 Corvus — For authorized healthcare personnel and enrolled participants only.
      </footer>
    </div>
  );
}
