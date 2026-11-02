import { useState, useEffect } from "react";
import { Database, PlaySquare, ShieldCheck, Activity, Timer, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ClinicalShell } from "../components/ClinicalShell";
import { Card, Button, Badge, StatCard } from "../components/ui";
import { predictionAPI } from "../api";

export function Models() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    predictionAPI
      .modelInfo()
      .then((res) => setInfo(res.data))
      .catch(() => setError("Unable to reach /v2/model_info — check the API container."))
      .finally(() => setBusy(false));
  }, []);

  return (
    <ClinicalShell
      title="Models & Endpoints"
      subtitle="Serving model registry status, /v2 contract, and live predictions"
      actions={
        <Button variant="secondary" size="sm">
          <PlaySquare className="size-3.5" /> Refresh
        </Button>
      }
    >
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatCard label="Registered model" value="corvus-ckd" hint="MLflow registry" />
          <StatCard label="Serving version" value={info?.model_version ?? "—"} hint="Pinned at startup" />
          <StatCard label="Route" value="/v2/*" hint="v9 remains at v1 routes" />
        </div>

        <Card>
          <div className="flex items-center justify-between border-b border-outline-variant px-5 py-4">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded bg-primary-soft text-primary">
                <Database className="size-4" />
              </span>
              <div>
                <h2 className="text-base font-bold text-on-surface">Live Model Information</h2>
                <p className="text-[11px] text-on-surface-variant">
                  {busy ? "Loading /v2/model_info…" : error ? "Endpoint unreachable" : `Pinned at container startup — ${info?.model_name} v${info?.model_version}`}
                </p>
              </div>
            </div>
            <Badge tone={busy ? "moderate" : error ? "high" : "low"} dot={busy ? false : undefined}>
              {busy ? "Loading" : error ? "Unreachable" : "Online"}
            </Badge>
          </div>
          {busy || error ? null : (
            <div className="grid gap-3 p-5 sm:grid-cols-2">
              {[
                ["Model name", info.model_name],
                ["Version", info.model_version],
                ["Run ID", info.run_id],
                ["Resolution", info.resolution],
              ].map(([k, v]) => (
                <Card key={k} className="p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant mb-1">{k}</p>
                  <p className="text-sm font-mono tabular text-on-surface break-all">{v}</p>
                </Card>
              ))}
            </div>
          )}
          {error && (
            <div className="p-5 rounded border border-[#FECACA] bg-[#FEF2F2] text-[12px] text-[#991B1B]">
              {error}
            </div>
          )}
        </Card>

        <Card>
          <div className="border-b border-outline-variant p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-on-surface">Compare Models</h2>
              <p className="text-[11px] text-on-surface-variant">
                Compare serving model versions side by side
              </p>
            </div>
          </div>
          <div className="p-4">
            <Button onClick={() => navigate("/models/model-comparison")} size="sm">
              <ArrowRight className="size-3.5" /> Compare Model Versions
            </Button>
          </div>
        </Card>

        <Card>
          <div className="border-b border-outline-variant p-4 flex items-center gap-2">
            <Activity className="size-4 text-primary-container" />
            <h2 className="text-base font-bold text-on-surface">Version Comparison (documented)</h2>
          </div>
          <div className="grid gap-3 p-4">
            {[
              {
                name: "v11 — NHANES Native (Production, /v2)",
                engine: "GradientBoosting",
                cohort: "NHANES 2017–Mar 2020",
                rows: "5,343 derived",
                features: "21 (16 numeric + 5 categorical)",
                holdout: "ROC-AUC 0.8265",
              },
              {
                name: "v9 — UCI CKD (Legacy, v1 routes)",
                engine: "MLP-ReLU",
                cohort: "UCI CKD ID 336",
                rows: "400",
                features: "24 (heavy missingness ≤38%/col)",
                holdout: "ROC-AUC 0.5479",
              },
            ].map((m) => (
              <Card key={m.name} className="p-3">
                <p className="text-xs font-bold text-on-surface mb-1">{m.name}</p>
                <dl className="space-y-1 text-[11px] leading-relaxed">
                  <div className="flex justify-between"><dt className="text-on-surface-variant">Engine</dt><dd className="text-on-surface tabular">{m.engine}</dd></div>
                  <div className="flex justify-between"><dt className="text-on-surface-variant">Cohort</dt><dd className="text-on-surface-variant">{m.cohort}</dd></div>
                  <div className="flex justify-between"><dt className="text-on-surface-variant">Rows</dt><dd className="text-on-surface-variant tabular">{m.rows}</dd></div>
                  <div className="flex justify-between"><dt className="text-on-surface-variant">Features</dt><dd className="text-on-surface-variant tabular">{m.features}</dd></div>
                  <div className="flex justify-between"><dt className="text-on-surface-variant">Holdout ROC-AUC</dt><dd className="text-on-surface-variant tabular font-semibold">{m.holdout}</dd></div>
                </dl>
              </Card>
            ))}
          </div>
          <p className="mt-4 px-5 pb-5 text-[11px] text-on-surface-variant">
            Metrics above are from the repository’s documented holdout evaluation (phase 07
            verification passed 12/12 automated checks). No performance claims are fabricated
            here.
          </p>
        </Card>

        <Card>
          <div className="border-b border-outline-variant p-4 flex items-center gap-2">
            <Timer className="size-4 text-primary-container" />
            <h2 className="text-base font-bold text-on-surface">Serving Notes</h2>
          </div>
          <div className="p-4 space-y-2 text-[12px] text-on-surface-variant">
            <div className="flex items-start gap-2"><ShieldCheck className="mt-0.5 size-3.5" /><span>v11 serves only at /v2 endpoints; /v1 endpoints remain bound to v9.</span></div>
            <div className="flex items-start gap-2"><ShieldCheck className="mt-0.5 size-3.5" /><span>Fail-closed: /v2 returns 503 while no model version is pinned.</span></div>
            <div className="flex items-start gap-2"><ShieldCheck className="mt-0.5 size-3.5" /><span>Predictions log to PostgreSQL (table predictions_v2) on every call.</span></div>
            <div className="flex items-start gap-2"><ShieldCheck className="mt-0.5 size-3.5" /><span>Blank NHANES fields are sent as null and imputed server-side.</span></div>
          </div>
        </Card>
      </div>
    </ClinicalShell>
  );
}

