import { useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, CheckCircle2, FileDown } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { predictionAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { NhanesForm } from "../components/NhanesForm";
import { Button, Card, ResultBadge, StatCard } from "../components/ui";
import { addPrediction, getPredictions } from "../lib/history";

export function Dashboard() {
  const { user } = useAuth();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState(getPredictions());

  const onSubmit = async (payload) => {
    setError("");
    setResult(null);
    try {
      const res = await predictionAPI.predict(payload);
      const entry = { ...res.data, payload };
      setResult(entry);
      setRecent(addPrediction(entry));
    } catch (err) {
      setError(err.response?.data?.detail || "Prediction failed. Check the API is reachable at http://localhost:8000.");
    }
  };

  return (
    <ClinicalShell
      title="NHANES Assessment"
      subtitle="Submit vitals and labs to call /v2/predict (Model v15)"
      actions={
        <Link to="/history">
          <Button variant="secondary" size="sm">
            <FileDown className="size-3.5" /> Prediction History
          </Button>
        </Link>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-lg font-bold text-on-surface">
              Welcome, {user?.email?.split("@")[0]}
            </p>
            <p className="text-sm text-on-surface-variant">
              Complete the NHANES-native fields for the GradientBoosting serving model.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded border border-[#A7F3D0] bg-[#ECFDF5] px-2 py-1 text-[11px] font-semibold text-[#065F46]">
              <CheckCircle2 className="size-3.5" /> /v2/predict active
            </span>
            <span className="inline-flex items-center gap-1.5 rounded border border-outline-variant px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
              v15
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <StatCard label="Assessments (this session)" value={recent.length} hint="Stored locally until history endpoint ships" />
          <StatCard label="Serving endpoint" value="/v2/predict" hint="POST • JSON • version-stamped" />
          <StatCard label="Serving model" value="v15" hint="GradientBoosting • NHANES-native" />
        </div>

        <Card>
          <div className="flex items-center justify-between gap-3 border-b border-outline-variant px-5 py-4">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded bg-primary-soft text-primary">
                <Activity className="size-4" />
              </span>
              <div>
                <h2 className="text-base font-bold text-on-surface">CKD Risk Assessment Form</h2>
                <p className="text-[11px] text-on-surface-variant">
                  Numeric fields accept decimal values. Categorical fields use NHANES codes.
                </p>
              </div>
            </div>
          </div>
          <div className="px-5 py-5">
            <NhanesForm onSubmit={onSubmit} submitLabel="Run /v2/predict" />
          </div>
        </Card>

        {error && (
          <div className="rounded border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 text-sm text-[#991B1B]">
            {error}
          </div>
        )}

        {result && (
          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant px-5 py-4">
              <div className="flex items-center gap-2">
                <ResultBadge prediction={result.prediction} />
                <h2 className="text-base font-bold text-on-surface">Prediction Result</h2>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-on-surface-variant">
                <span className="rounded border border-outline-variant px-2 py-0.5 font-mono">model_version: {result.model_version}</span>
                <span className="rounded border border-outline-variant px-2 py-0.5 font-mono">endpoint: /v2/predict</span>
              </div>
            </div>
            <div className="flex flex-col gap-4 px-5 py-5 lg:flex-row lg:items-center">
              <div className="flex min-w-[220px] items-baseline gap-2">
                <span className="text-3xl font-bold tabular text-on-surface">
                  {(result.probability * 100).toFixed(1)}%
                </span>
                <span className="text-sm text-on-surface-variant">CKD probability</span>
              </div>
              <div className="flex-1">
                <div className="h-3 w-full overflow-hidden rounded-full bg-surface-container">
                  <div
                    className={`h-full ${result.prediction === 1 ? "bg-[#DC2626]" : "bg-[#059669]"}`}
                    style={{ width: `${Math.max(4, Math.round(result.probability * 100))}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-[11px] text-on-surface-variant tabular">
                  <span>0.0</span>
                  <span>Decision cutoff ~ 0.50</span>
                  <span>1.0</span>
                </div>
              </div>
              <Link to="/history">
                <Button variant="secondary" size="md">
                  View history <ArrowRight className="size-3.5" />
                </Button>
              </Link>
            </div>
          </Card>
        )}
      </div>
    </ClinicalShell>
  );
}
