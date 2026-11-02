import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Filter, MoreVertical, Search, UserPlus } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { ClinicalShell } from "../components/ClinicalShell";
import { Button, Card, Badge, StatCard, ResultBadge } from "../components/ui";
import { ROSTER } from "../data/sample";

export function DoctorDashboard() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("all");
  const [model, setModel] = useState("all");

  const filtered = useMemo(() => {
    return ROSTER.filter((p) => {
      const q = query.toLowerCase();
      const matchesQuery =
        !q || p.name.toLowerCase().includes(q) || p.mrn.toLowerCase().includes(q);
      const matchesRisk =
        risk === "all"
          ? true
          : risk === "flagged"
          ? p.prediction === 1
          : p.prediction === 0;
      const matchesModel =
        model === "all" ? true : String(p.modelVersion) === model;
      return matchesQuery && matchesRisk && matchesModel;
    }).sort((a, b) => {
      const ra = a.prediction === 1 ? 1 : a.prediction === null ? 0 : -1;
      const rb = b.prediction === 1 ? 1 : b.prediction === null ? 0 : -1;
      return rb - ra;
    });
  }, [query, risk, model]);

  const flagged = ROSTER.filter((p) => p.prediction === 1).length;
  const pending = ROSTER.filter((p) => p.prediction === null).length;

  return (
    <ClinicalShell
      title="Doctor Dashboard"
      subtitle={`Nephrology service • ${user?.email}`}
      actions={
        <>
          <Button variant="secondary" size="sm">
            <Download className="size-3.5" /> Batch Export
          </Button>
          <Button size="sm">
            <UserPlus className="size-3.5" /> Add Patient
          </Button>
        </>
      }
    >
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-lg font-bold text-on-surface">
              Welcome back, Dr. {user?.email?.split("@")[0]}
            </p>
            <p className="text-sm text-on-surface-variant">
              Review predictions, triage flagged patients, and inspect history by patient.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatCard label="Assigned Patients" value={ROSTER.length} hint="+2 this week" />
          <Card className="min-w-[158px] flex-1 p-4 border-error-container">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-on-surface">CKD Flagged</p>
              <span className="relative flex size-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-error opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-error" />
              </span>
            </div>
            <p className="mt-1 text-2xl font-bold text-tertiary tabular">{flagged}</p>
            <p className="mt-0.5 text-[11px] text-on-surface-variant">-1 triage cleared</p>
          </Card>
          <StatCard label="Pending Reviews" value={pending} hint="+1 awaiting labs" />
        </div>

        <Card>
          <div className="flex flex-col gap-3 border-b border-outline-variant p-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full max-w-md">
              <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-outline" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="h-8 w-full rounded border border-outline-variant bg-surface-lowest pl-8 pr-2.5 text-sm text-on-surface placeholder:text-[#8a8f9e] focus:border-primary-container focus:outline-none focus:ring-1 focus:ring-primary-container"
                placeholder="Search by patient name or MRN..."
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex rounded border border-outline-variant bg-surface-low p-0.5 text-[11px] font-semibold">
                {[
                  { key: "all", label: `All [${ROSTER.length}]` },
                  { key: "flagged", label: `CKD Flagged [${flagged}]` },
                  { key: "healthy", label: `Healthy [${ROSTER.length - flagged - pending}]` },
                ].map((opt) => (
                  <button
                    key={opt.key}
                    onClick={() => setRisk(opt.key)}
                    className={`rounded px-2.5 py-1 ${
                      risk === opt.key ? "bg-surface-lowest text-primary shadow-sm" : "text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <div className="relative">
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="h-8 appearance-none rounded border border-outline-variant bg-surface-lowest px-2.5 pr-7 text-[11px] font-semibold text-on-surface focus:border-primary-container focus:outline-none focus:ring-1 focus:ring-primary-container"
                >
                  <option value="all">All Models</option>
                  <option value="11">v11 (NHANES)</option>
                  <option value="9">v9 (UCI CKD)</option>
                </select>
                <Filter className="pointer-events-none absolute right-2 top-1/2 size-3.5 -translate-y-1/2 text-outline" />
              </div>
              <Button variant="ghost" size="sm" className="px-2">
                <Download className="size-3.5" />
              </Button>
            </div>
          </div>

          <div className="scrollbar-slim overflow-x-auto">
            <table className="w-full min-w-[880px] text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-low text-[10px] uppercase tracking-wider text-on-surface-variant">
                  <th className="px-4 py-2 font-semibold">Patient</th>
                  <th className="px-3 py-2 font-semibold">Role</th>
                  <th className="px-3 py-2 font-semibold">Last Prediction</th>
                  <th className="px-3 py-2 font-semibold">Risk Result / Probability</th>
                  <th className="px-3 py-2 font-semibold">Model</th>
                  <th className="px-3 py-2 font-semibold">Risk Status</th>
                  <th className="px-4 py-2 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {filtered.map((p) => (
                  <tr key={p.id} className="group hover:bg-surface-low/70">
                    <td className="px-4 py-2.5">
                      <Link to={`/patients/${p.id}`} className="font-semibold text-on-surface hover:underline">
                        {p.name}
                      </Link>
                      <p className="text-[11px] text-on-surface-variant tabular">
                        {p.mrn} • {p.age}yo {p.sex}
                      </p>
                    </td>
                    <td className="px-3 py-2.5 text-[11px] text-on-surface-variant">Patient</td>
                    <td className="px-3 py-2.5 text-[11px] text-on-surface-variant tabular">{p.lastAt}</td>
                    <td className="px-3 py-2.5">
                      {p.prediction === null ? (
                        <span className="text-[11px] font-semibold text-[#92400E]">Pending Labs</span>
                      ) : (
                        <ResultBadge prediction={p.prediction} />
                      )}
                      <p className="mt-0.5 text-[11px] text-on-surface-variant tabular">
                        {p.probability === null ? "Awaiting serum creatinine" : `p = ${p.probability.toFixed(3)} (${(p.probability * 100).toFixed(1)}%)`}
                      </p>
                    </td>
                    <td className="px-3 py-2.5">
                      {p.modelVersion ? (
                        <Badge tone="neutral" className="normal-case">
                          v{p.modelVersion} {p.modelVersion === "11" ? "(NHANES)" : "(UCI)"}
                        </Badge>
                      ) : (
                        <Badge tone="neutral" className="normal-case">
                          Pending
                        </Badge>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      {p.prediction === 1 && <Badge tone="high">High Risk</Badge>}
                      {p.prediction === 0 && <Badge tone="low">Healthy</Badge>}
                      {p.prediction === null && <Badge tone="moderate">Lab Pending</Badge>}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="inline-flex items-center gap-1">
                        <Link to={`/patients/${p.id}`}>
                          <Button variant="secondary" size="sm">
                            View Detail
                          </Button>
                        </Link>
                        <button className="rounded p-1 text-on-surface-variant hover:bg-surface-low">
                          <MoreVertical className="size-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-outline-variant px-4 py-2 text-[11px] text-on-surface-variant">
            <span>
              Showing <span className="font-semibold text-on-surface">{filtered.length}</span> of{" "}
              <span className="font-semibold text-on-surface">{ROSTER.length}</span> patients
            </span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" disabled>
                Previous
              </Button>
              <Button variant="secondary" size="sm">
                Next
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </ClinicalShell>
  );
}
