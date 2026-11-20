import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, ShieldCheck, Stethoscope, UserRound } from "lucide-react";
import { useAuth } from "../contexts/authStore";
import { authAPI } from "../api";
import { AuthLayout } from "../components/AuthLayout";
import { Alert, Button, Card, Field, Input, Spinner } from "../components/ui";

// Demo accounts that actually exist in the seeded database. The previous
// values (dr.jenkins@corvushealth.org / maria.gonzalez@patient...) were never
// created, so "Sign In" with the prefilled form always returned 401.
const DEMO = {
  doctor: { email: "clinician@corvus-demo.com", password: "Clinic123!" },
  patient: { email: "verifier@example.com", password: "Verify123!" },
};

export function ClinicalLogin() {
  const [role, setRole] = useState("doctor");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const select = (nextRole) => {
    setRole(nextRole);
    setError("");
  };

  const fillDemo = () => {
    setEmail(DEMO[role].email);
    setPassword(DEMO[role].password);
    setError("");
  };

  const handle = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authAPI.login({ email, password });
      // Redirect on the role the server reports, not the cosmetic toggle.
      const userData = await login(res.data.access_token);
      navigate(userData?.role === "doctor" ? "/doctor-dashboard" : "/dashboard", {
        replace: true,
      });
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "Could not sign in. Check the email and password and try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const portalTab = (value, label, Icon) => {
    const active = role === value;
    return (
      <button
        type="button"
        onClick={() => select(value)}
        aria-pressed={active}
        className={`flex min-h-9 items-center justify-center gap-1.5 rounded px-3 text-xs font-semibold transition-colors ${
          active
            ? "bg-surface-lowest text-primary shadow-sm"
            : "text-on-surface-variant hover:text-on-surface"
        }`}
      >
        <Icon className="size-4" aria-hidden="true" />
        {label}
      </button>
    );
  };

  return (
    <AuthLayout>
      <Card className="overflow-hidden">
        <div className="border-b border-outline-variant px-6 py-6 sm:px-8">
          <h1 className="text-xl font-bold tracking-tight text-on-surface sm:text-2xl">
            Sign in
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            {role === "doctor"
              ? "Clinical console: patient roster, risk triage and model versions."
              : "Patient portal: submit labs and vitals, review your risk history."}
          </p>

          <div className="mt-5 grid grid-cols-2 gap-1 rounded border border-outline-variant bg-surface-low p-1">
            {portalTab("doctor", "Clinician", Stethoscope)}
            {portalTab("patient", "Patient", UserRound)}
          </div>
        </div>

        <form onSubmit={handle} className="space-y-4 px-6 py-6 sm:px-8">
          <Field label="Email address" htmlFor="email" required>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@clinic.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>

          <Field label="Password" htmlFor="password" required>
            <div className="relative">
              <Input
                id="password"
                type={show ? "text" : "password"}
                autoComplete="current-password"
                required
                className="pr-11"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-1 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded text-on-surface-variant hover:bg-surface-low"
                aria-label={show ? "Hide password" : "Show password"}
              >
                {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </Field>

          {error && <Alert tone="danger">{error}</Alert>}

          <Button type="submit" size="lg" className="w-full" disabled={loading}>
            {loading ? <Spinner /> : <ArrowRight className="size-4" aria-hidden="true" />}
            {loading ? "Signing in…" : `Sign in as ${role === "doctor" ? "clinician" : "patient"}`}
          </Button>

          <p className="text-center text-xs text-on-surface-variant">
            Need an account?{" "}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Register
            </Link>
          </p>
        </form>

        <div className="border-t border-outline-variant bg-surface-low px-6 py-4 sm:px-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-on-surface-variant">
              <ShieldCheck className="size-4 text-primary" aria-hidden="true" />
              Demo {role === "doctor" ? "clinician" : "patient"} account
            </span>
            <Button type="button" variant="secondary" size="sm" onClick={fillDemo}>
              Fill demo credentials
            </Button>
          </div>
          <p className="mt-2 font-mono text-xs text-on-surface-variant">{DEMO[role].email}</p>
        </div>
      </Card>
    </AuthLayout>
  );
}
