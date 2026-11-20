import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart3, Database, Info, RefreshCw, ShieldCheck } from "lucide-react";
import { ClinicalShell } from "../components/ClinicalShell";
import { Alert, Badge, Button, Card, CardHeader, Skeleton, StatCard } from "../components/ui";
import { predictionAPI } from "../api";
import {
  DATA_NOTES,
  DECISION_THRESHOLD,
  FEATURE_COUNT,
  METRICS,
  MODEL_ALGORITHM,
  MODEL_PARAMS,
  MODEL_RUN_ID,
  MODEL_VERSION,
} from "../data/model";

const pct = (value) => `${(value * 100).toFixed(1)}%`;

const PERFORMANCE = [
  { label: "Holdout ROC-AUC", value: METRICS.rocAuc.toFixed(4), note: `95% CI ${METRICS.rocAucCi[0].toFixed(3)}–${METRICS.rocAucCi[1].toFixed(3)}` },
  { label: "Holdout PR-AUC", value: METRICS.prAuc.toFixed(4), note: "Primary ranking metric at low prevalence" },
  { label: "Recall (sensitivity)", value: pct(METRICS.recall), note: "Share of true CKD cases flagged" },
  { label: "Precision (PPV)", value: pct(METRICS.precision), note: "Share of flags that are true cases" },
  { label: "F1", value: METRICS.f1.toFixed(4), note: `At threshold ${DECISION_THRESHOLD.toFixed(3)}` },
  { label: "Accuracy", value: pct(METRICS.accuracy), note: "Close to base rate — do not use alone" },
  { label: "Brier score", value: METRICS.brier.toFixed(4), note: "Probability calibration, lower is better" },
  { label: "CV ROC-AUC (5-fold)", value: `${METRICS.cvMeanAuc.toFixed(4)} ± ${METRICS.cvStdAuc.toFixed(4)}`, note: "Training stability" },
];

export function Models() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  const load = useCallback(async (options = {}) => {
    if (options.reset !== false) {
      setBusy(true);
      setError("");
    }
    try {
      const res = await predictionAPI.modelInfo();
      setInfo(res.data);
    } catch {
      setError("Could not reach /v2/model_info. The API container may be down.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch syncs with the API; loading is already true.
    // oxlint-disable-next-line react/set-state-in-effect
    load({ reset: false });
  }, [load]);

  return (
    <ClinicalShell
      title="Model performance"
      subtitle={`corvus-ckd v${MODEL_VERSION} · ${MODEL_ALGORITHM}`}
      actions={
        <Button variant="secondary" size="sm" onClick={load} disabled={busy}>
          <RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh
        </Button>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Serving version" value={`v${info?.model_version ?? MODEL_VERSION}`} hint="Pinned at container startup" icon={Database} />
          <StatCard label="Holdout ROC-AUC" value={METRICS.rocAuc.toFixed(4)} hint="NHANES 2021-2023 holdout" icon={BarChart3} />
          <StatCard label="Decision threshold" value={DECISION_THRESHOLD.toFixed(3)} hint="Tuned for recall, not precision" />
        </div>

        <Card>
          <CardHeader
            icon={Database}
            title="Live model information"
            description={busy ? "Loading /v2/model_info…" : error ? "Endpoint unreachable" : "Values below are read from the serving container, not hardcoded."}
            actions={<Badge tone={busy ? "moderate" : error ? "high" : "low"} dot>{busy ? "Loading" : error ? "Unreachable" : "Online"}</Badge>}
          />
          <div className="p-5">
            {error ? (
              <Alert tone="danger" title="Model info unavailable">{error}</Alert>
            ) : busy ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : (
              <dl className="grid gap-3 sm:grid-cols-2">
                {[
                  ["Model name", info.model_name],
                  ["Version", info.model_version],
                  ["Run ID", info.run_id],
                  ["Resolution", info.resolution],
                ].map(([label, value]) => (
                  <div key={label} className="rounded border border-outline-variant bg-surface-low px-3 py-2.5">
                    <dt className="text-xs font-medium text-on-surface-variant">{label}</dt>
                    <dd className="mt-0.5 break-all font-mono text-sm tabular text-on-surface">{value ?? "—"}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            icon={BarChart3}
            title="Holdout metrics"
            description={`Run ${MODEL_RUN_ID.slice(0, 8)} · ${FEATURE_COUNT} features · ${MODEL_PARAMS}`}
          />
          <div className="divide-y divide-outline-variant">
            {PERFORMANCE.map((metric) => (
              <div key={metric.label} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-on-surface">{metric.label}</p>
                  <p className="text-xs text-on-surface-variant">{metric.note}</p>
                </div>
                <p className="font-mono text-sm font-semibold tabular text-on-surface">{metric.value}</p>
              </div>
            ))}
          </div>
          <p className="border-t border-outline-variant bg-surface-low px-5 py-3 text-xs leading-relaxed text-on-surface-variant">
            The model is tuned for recall: at the serving threshold it catches about 84% of true cases while roughly
            two thirds of flags are false positives. Treat every flag as a prompt for confirmatory testing.
          </p>
        </Card>

        <Card>
          <CardHeader icon={Info} title="Data and label provenance" description="What the model was trained on, in plain terms." />
          <ul className="space-y-2.5 p-5">
            {DATA_NOTES.map((note) => (
              <li key={note} className="flex items-start gap-2.5 text-sm leading-relaxed text-on-surface-variant">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                {note}
              </li>
            ))}
          </ul>
        </Card>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-outline-variant bg-surface-lowest px-5 py-4">
          <div>
            <p className="text-sm font-medium text-on-surface">Version comparison</p>
            <p className="text-xs text-on-surface-variant">Serving v15 next to the legacy UCI model on /v1.</p>
          </div>
          <Button as={Link} to="/models/model-comparison" variant="secondary" size="sm">
            Compare versions
          </Button>
        </div>
      </div>
    </ClinicalShell>
  );
}
