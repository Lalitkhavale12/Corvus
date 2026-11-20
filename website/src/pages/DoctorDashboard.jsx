import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FlaskConical, RefreshCw, Search, UserPlus, Users } from "lucide-react";
import { useAuth } from "../contexts/authStore";
import { predictionAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, ResultBadge, Skeleton, StatCard, Table, TBody, TD, TH, THead } from "../components/ui";
import { ROSTER } from "../data/sample";

const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export function DoctorDashboard() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("all");

  const load = useCallback((options = {}) => {
    if (options.reset !== false) {
      setLoading(true);
      setError("");
    }
    predictionAPI
      .getDoctorPatients()
      .then((res) => setAssignments(res.data || []))
      .catch(() => setError("Could not load your patient assignments."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // Initial fetch syncs with the API; loading is already true.
    // oxlint-disable-next-line react/set-state-in-effect
    load({ reset: false });
  }, [load]);

  const active = assignments.filter((row) => row.is_active);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return ROSTER.filter((p) => {
      const matchesQuery = !q || p.name.toLowerCase().includes(q) || p.mrn.toLowerCase().includes(q);
      const matchesRisk = risk === "all" || (risk === "flagged" ? p.prediction === 1 : p.prediction === 0);
      return matchesQuery && matchesRisk;
    });
  }, [query, risk]);

  const flagged = ROSTER.filter((p) => p.prediction === 1).length;
  const healthy = ROSTER.filter((p) => p.prediction === 0).length;

  return (
    <ClinicalShell
      title="Patient roster"
      subtitle={user?.email}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
            Refresh
          </Button>
          <Button as={Link} to="/assign-patients" size="sm">
            <UserPlus className="size-4" aria-hidden="true" />
            Assign patient
          </Button>
        </>
      }
    >
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Assigned patients" value={loading ? "—" : assignments.length} hint="From the assignment service" icon={Users} />
          <StatCard label="Active assignments" value={loading ? "—" : active.length} hint="is_active = true" />
          <StatCard label="Inactive" value={loading ? "—" : assignments.length - active.length} hint="Assignment revoked" />
        </div>

        <Card>
          <CardHeader
            icon={Users}
            title="Live assignments"
            description="Real rows from GET /doctors/patients. The API returns the mapping only — no patient demographics or predictions."
          />
          {error ? (
            <div className="p-5">
              <Alert tone="danger" title="Assignments unavailable">{error}</Alert>
            </div>
          ) : loading ? (
            <div className="space-y-2 p-5">
              {[0, 1].map((i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : assignments.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No patients assigned"
              body="Assign a patient by email and their record will appear here."
              action={
                <Button as={Link} to="/assign-patients" size="sm">
                  Assign a patient
                </Button>
              }
            />
          ) : (
            <div className="px-5 py-4">
              <Table minWidth={520}>
                <THead>
                  <tr>
                    <TH>Patient ID</TH>
                    <TH>Status</TH>
                    <TH>Assigned</TH>
                    <TH className="text-right">Record</TH>
                  </tr>
                </THead>
                <TBody>
                  {assignments.map((row) => (
                    <tr key={row.id}>
                      <TD className="font-mono tabular">#{row.patient_id}</TD>
                      <TD>
                        <Badge tone={row.is_active ? "low" : "neutral"} dot>
                          {row.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TD>
                      <TD className="tabular text-on-surface-variant">
                        {row.assigned_at ? dateFmt.format(new Date(row.assigned_at)) : "—"}
                      </TD>
                      <TD className="text-right">
                        <Button as={Link} to={`/patients/${row.patient_id}`} variant="secondary" size="sm">
                          Open
                        </Button>
                      </TD>
                    </tr>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
        </Card>

        <Card>
          <div className="border-b border-outline-variant bg-warning-soft px-5 py-3">
            <p className="flex items-center gap-2 text-sm font-medium text-warning-ink">
              <FlaskConical className="size-4 shrink-0" aria-hidden="true" />
              Illustrative preview — sample data, not real patients
            </p>
            <p className="mt-1 pl-6 text-xs leading-relaxed text-warning-ink/90">
              There is no per-patient prediction endpoint yet, so this table uses invented records to demonstrate the
              triage layout. Nothing here reflects a real person or a real model run.
            </p>
          </div>

          <div className="flex flex-col gap-3 border-b border-outline-variant p-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full max-w-sm">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-outline" aria-hidden="true" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search sample patients"
                className="h-9 w-full rounded border border-outline-variant bg-surface-lowest pl-8 pr-2.5 text-sm text-on-surface placeholder:text-outline focus:border-primary-container focus:outline-none focus:ring-1 focus:ring-primary-container"
                placeholder="Search sample name or MRN"
              />
            </div>
            <div className="flex flex-wrap items-center gap-1 rounded border border-outline-variant bg-surface-low p-1" role="tablist" aria-label="Filter by risk">
              {[
                { key: "all", label: `All (${ROSTER.length})` },
                { key: "flagged", label: `Flagged (${flagged})` },
                { key: "healthy", label: `Healthy (${healthy})` },
              ].map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  role="tab"
                  aria-selected={risk === opt.key}
                  onClick={() => setRisk(opt.key)}
                  className={`min-h-8 rounded px-3 text-xs font-semibold transition-colors ${
                    risk === opt.key
                      ? "bg-surface-lowest text-primary shadow-sm"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="px-5 py-4">
            <Table minWidth={760}>
              <THead>
                <tr>
                  <TH>Patient</TH>
                  <TH>Last run</TH>
                  <TH>Result</TH>
                  <TH>Probability</TH>
                  <TH>Model</TH>
                </tr>
              </THead>
              <TBody>
                {filtered.map((p) => (
                  <tr key={p.id}>
                    <TD>
                      <Link to={`/patients/${p.id}`} className="inline-flex min-h-8 items-center font-medium text-on-surface hover:underline">
                        {p.name}
                      </Link>
                      <p className="text-xs tabular text-on-surface-variant">
                        {p.mrn} · {p.age}yo {p.sex}
                      </p>
                    </TD>
                    <TD className="tabular text-on-surface-variant">{p.lastAt}</TD>
                    <TD>
                      {p.prediction === null ? (
                        <Badge tone="moderate" dot>Labs pending</Badge>
                      ) : (
                        <ResultBadge prediction={p.prediction} />
                      )}
                    </TD>
                    <TD className="font-mono tabular">
                      {p.probability === null ? "—" : p.probability.toFixed(3)}
                    </TD>
                    <TD>
                      <Badge tone="neutral">{p.modelVersion ? `v${p.modelVersion}` : "—"}</Badge>
                    </TD>
                  </tr>
                ))}
              </TBody>
            </Table>
            <p className="mt-3 text-xs text-on-surface-variant">
              Showing {filtered.length} of {ROSTER.length} sample records.
            </p>
          </div>
        </Card>
      </div>
    </ClinicalShell>
  );
}
