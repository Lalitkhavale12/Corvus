import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Clock3, RefreshCw } from "lucide-react";
import { useAuth } from "../contexts/authStore";
import { predictionAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, ResultBadge, Skeleton, StatCard, Table, TBody, TD, TH, THead } from "../components/ui";

const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const ordered = (rows) =>
  rows.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

export function PredictionHistory() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = (options = {}) => {
    if (options.reset !== false) {
      setLoading(true);
      setError("");
    }
    predictionAPI
      .getHistory()
      .then((res) => setHistory(ordered(res.data || [])))
      .catch(() => setError("Could not load your prediction history."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // Initial fetch syncs with the API; loading is already true.
    // oxlint-disable-next-line react/set-state-in-effect
    load({ reset: false });
  }, []);

  const summary = useMemo(() => {
    const flagged = history.filter((row) => row.prediction === 1).length;
    const probs = history.map((row) => row.probability).filter((p) => typeof p === "number");
    return {
      total: history.length,
      flagged,
      latest: history[0]?.created_at ? dateFmt.format(new Date(history[0].created_at)) : "—",
      mean: probs.length ? (probs.reduce((a, b) => a + b, 0) / probs.length).toFixed(3) : "—",
    };
  }, [history]);

  return (
    <ClinicalShell
      title="Prediction history"
      subtitle={user?.email}
      actions={
        <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh
        </Button>
      }
    >
      <div className="mx-auto max-w-5xl space-y-5">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Total predictions" value={summary.total} />
          <StatCard label="Flagged for CKD" value={summary.flagged} hint="Screening flags, not diagnoses" />
          <StatCard label="Mean probability" value={summary.mean} />
          <StatCard label="Most recent" value={summary.latest} />
        </div>

        <Card>
          <CardHeader
            icon={Clock3}
            title="All runs"
            description="Every assessment stored against your account, newest first."
          />

          {error ? (
            <div className="p-5">
              <ErrorState title="History unavailable" body={error} onRetry={load} />
            </div>
          ) : loading ? (
            <div className="space-y-2 p-5">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : history.length === 0 ? (
            <EmptyState
              icon={Clock3}
              title="No predictions yet"
              body="Run an assessment and the result will be stored here with its model version."
              action={
                <Button as={Link} to="/dashboard" size="sm">
                  Start an assessment
                </Button>
              }
            />
          ) : (
            <>
              <div className="px-5 pb-2 pt-4">
                <Table minWidth={560}>
                  <THead>
                    <tr>
                      <TH>Date</TH>
                      <TH>Result</TH>
                      <TH className="text-right">Probability</TH>
                      <TH className="text-right">Model</TH>
                    </tr>
                  </THead>
                  <TBody>
                    {history.map((entry) => (
                      <tr key={entry.id}>
                        <TD>
                          <span className="tabular">{entry.created_at ? dateFmt.format(new Date(entry.created_at)) : "—"}</span>
                          <span className="ml-2 font-mono text-xs text-on-surface-variant">#{entry.id}</span>
                        </TD>
                        <TD><ResultBadge prediction={entry.prediction} /></TD>
                        <TD className="text-right font-mono tabular">
                          {typeof entry.probability === "number" ? entry.probability.toFixed(4) : "—"}
                        </TD>
                        <TD className="text-right">
                          <Badge tone="neutral">v{entry.model_version}</Badge>
                        </TD>
                      </tr>
                    ))}
                  </TBody>
                </Table>
              </div>
              <p className="border-t border-outline-variant bg-surface-low px-5 py-3 text-xs leading-relaxed text-on-surface-variant">
                The history endpoint returns the result and model version only — the submitted lab values are not
                stored, so this table cannot show inputs.
              </p>
            </>
          )}
        </Card>
      </div>
    </ClinicalShell>
  );
}
