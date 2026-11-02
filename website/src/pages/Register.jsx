import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity, CheckCircle2, Stethoscope, UserRound } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { authAPI } from "../api";
import { CorvusMark } from "../components/ClinicalShell";
import { Button, Card, Field, Input, Spinner } from "../components/ui";

export function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("patient");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authAPI.register({ email, password, role });
      const res = await authAPI.login({ email, password });
      await login(res.data.access_token);
      navigate(role === "doctor" ? "/doctor-dashboard" : "/dashboard", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-ckd-soft-gradient bg-nephron-pattern">
      <header className="border-b border-outline-variant bg-surface-lowest/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/login" className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded bg-primary-container text-on-primary">
              <CorvusMark className="size-5" />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-primary">Corvus Health</p>
              <p className="text-[10px] font-mono uppercase tracking-wider text-on-surface-variant">
                Enrollment
              </p>
            </div>
          </Link>
          <span className="kidney-badge">
            <span className="size-3.5 text-secondary">🫀</span>
            CKD Console
          </span>
          <Link to="/login" className="text-[11px] font-medium text-primary hover:underline">
            Back to sign in
          </Link>
          <Link to="/login" className="text-[11px] font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <Card className="w-full max-w-md overflow-hidden shadow-sm">
          <div className="border-b border-outline-variant px-6 py-6 sm:px-8">
            <h1 className="text-xl font-bold tracking-tight text-on-surface">Create account</h1>
            <p className="mt-1 text-sm text-on-surface-variant">
              Self-registration is enabled for both roles. No admin gate.
            </p>
          </div>

          <form onSubmit={submit} className="space-y-4 px-6 py-6 sm:px-8">
            <Field label="Email Address" htmlFor="email">
              <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>

            <Field label="Password" htmlFor="password">
              <Input
                id="password"
                type="password"
                minLength={6}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>

            <Field label="Role" htmlFor="role">
              <div className="grid grid-cols-2 gap-1 rounded border border-outline-variant bg-surface-low p-1">
                <button
                  type="button"
                  onClick={() => setRole("patient")}
                  className={`flex items-center justify-center gap-1.5 rounded py-1.5 text-xs font-semibold ${
                    role === "patient" ? "bg-surface-lowest text-primary shadow-sm" : "text-on-surface-variant"
                  }`}
                >
                  <UserRound className="size-3.5" /> Patient
                </button>
                <button
                  type="button"
                  onClick={() => setRole("doctor")}
                  className={`flex items-center justify-center gap-1.5 rounded py-1.5 text-xs font-semibold ${
                    role === "doctor" ? "bg-surface-lowest text-primary shadow-sm" : "text-on-surface-variant"
                  }`}
                >
                  <Stethoscope className="size-3.5" /> Doctor
                </button>
              </div>
            </Field>

            {error && (
              <div className="rounded border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#991B1B]">
                {error}
              </div>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={loading}>
              {loading ? <Spinner /> : <Activity className="size-4" />}
              {loading ? "Creating account…" : "Create account"}
            </Button>

            <div className="flex items-center gap-2 text-[11px] text-on-surface-variant">
              <CheckCircle2 className="size-3.5 text-secondary" />
              Email/password only • JWT session • CKD scope
            </div>
          </form>
        </Card>
      </main>
    </div>
  );
}
