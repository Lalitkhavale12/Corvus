import { useEffect, useState } from "react";
import { ArrowRight, Clock3 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { predictionAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { Badge, Card, EmptyState, fmtProbability } from "../components/ui";

export function PredictionHistory() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    predictionAPI
      .getHistory()
      .then((res) => {
        setHistory(res.data || []);
      })
      .catch((_err) => {
        setError("Unable to load prediction history");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="mx-auto max-w-5xl py-8"><div className="animate-pulse rounded bg-surface-container h-8 w-1/3 mx-auto" /></div>;

  return (
    <ClinicalShell
      title="Prediction History"
      subtitle={`Model runs for ${user?.email}`}
      actions={<></>}
    >
      <div className="mx-auto max-w-5xl space-y-4">
        <Card>
          <div className="border-b border-outline-variant p-4 flex items-center gap-2">
            <Clock3 className="size-4 text-primary-container" />
            <h2 className="text-base font-bold text-on-surface">Model Runs</h2>
            <span className="ml-auto rounded border border-outline-variant px-2 py-0.5 text-[10px] font-semibold text-on-surface-variant tabular">
              {history.length} predictions
            </span>
          </div>

          {error && (
            <div className="px-3 py-2 rounded border border-[#FECACA] bg-[#FEF2F2] text-xs text-[#991B1B]">
              {error}
            </div>
          )}

          {history.length === 0 ? (
            <EmptyState
              icon={Clock3}
              title="No predictions yet"
              body="Complete an assessment on the dashboard to see your version-stamped results here."
              action={
                <ArrowRight asChild className="px-4 py-2 bg-primary-container text-on-primary rounded text-xs font-semibold hover:bg-primary">
                  <a href="/dashboard">Run /v2/predict</a>
                </ArrowRight>
              }
            />
          ) : (
            <div className="p-4 space-y-3">
              {history
                .slice()
                .sort(
                  (a, b) =>
                    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                )
                .map((entry) => (
                  <Card key={entry.id} className="p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 md:flex-row md:justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold tabular text-on-surface-variant">
                          {entry.prediction === 1 ? "CKD Detected" : "No CKD Detected"}
                        </span>
                        <span className="text-[10px] font-mono tabular text-on-surface-variant">
                          {entry.probability === null ? "—" : fmtProbability(entry.probability)}
                        </span>
                        <span className="rounded border border-outline-variant px-2 py-0.5 text-[10px] font-semibold text-on-surface-variant">
                          v{entry.model_version}
                        </span>
                        <Badge tone={entry.prediction === 1 ? "high" : "low"} dot={false}>
                          {entry.prediction === 1 ? "CKD" : "Healthy"}
                        </Badge>
                      </div>
                      <div className="flex items-end gap-2">
                        <span className="font-mono tabular text-xs text-on-surface-variant">
                          {new Date(entry.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </Card>
                ))}
            </div>
          )}
        </Card>
      </div>
    </ClinicalShell>
  );
}
