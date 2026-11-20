import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity, Stethoscope, UserRound } from "lucide-react";
import { useAuth } from "../contexts/authStore";
import { authAPI } from "../api";
import { AuthLayout } from "../components/AuthLayout";
import { Alert, Button, Card, Field, Input, Spinner } from "../components/ui";

const ROLES = [
  { value: "patient", label: "Patient", icon: UserRound, home: "/dashboard" },
  { value: "doctor", label: "Clinician", icon: Stethoscope, home: "/doctor-dashboard" },
];

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
      const me = await login(res.data.access_token);
      const home = ROLES.find((r) => r.value === (me?.role ?? role))?.home ?? "/dashboard";
      navigate(home, { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed. Try a different email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card className="p-6 sm:p-7">
        <h2 className="text-xl font-semibold tracking-tight text-on-surface">Create an account</h2>
        <p className="mt-1 text-sm text-on-surface-variant">
          Self-registration is open for both roles. You can complete your profile after signing in.
        </p>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <Field label="Email address" htmlFor="email">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@clinic.org"
            />
          </Field>

          <Field label="Password" htmlFor="password" hint="At least 6 characters.">
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              minLength={6}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium text-on-surface">Role</legend>
            <div className="grid grid-cols-2 gap-1.5">
              {ROLES.map(({ value, label, icon: Icon }) => {
                const selected = role === value;
                return (
                  <label
                    key={value}
                    className={`flex cursor-pointer items-center justify-center gap-1.5 rounded border px-3 py-2 text-sm font-medium transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-primary-container ${
                      selected
                        ? "border-primary-line bg-primary-soft text-primary"
                        : "border-outline-variant bg-surface-lowest text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
                    }`}
                  >
                    <input
                      type="radio"
                      name="role"
                      value={value}
                      checked={selected}
                      onChange={() => setRole(value)}
                      className="sr-only"
                    />
                    <Icon className="size-4" aria-hidden="true" />
                    {label}
                  </label>
                );
              })}
            </div>
          </fieldset>

          {error && <Alert tone="danger">{error}</Alert>}

          <Button type="submit" size="lg" className="w-full" disabled={loading}>
            {loading ? <Spinner /> : <Activity className="size-4" aria-hidden="true" />}
            {loading ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-on-surface-variant">
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </Card>
    </AuthLayout>
  );
}
