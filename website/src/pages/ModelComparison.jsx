import { Link } from "react-router-dom";
import { Info } from "lucide-react";
import { ClinicalShell } from "../components/ClinicalShell";
import { Alert, Badge, Button, Card, CardHeader, Table, TBody, TD, TH, THead } from "../components/ui";
import { DECISION_THRESHOLD, FEATURE_COUNT, METRICS, MODEL_ALGORITHM, MODEL_VERSION } from "../data/model";

// The registry comparison/promotion endpoints (/api/v1/models*) return 500 in
// this deployment, so this page documents the two known model generations from
// verified artifacts instead of pretending to compare them live.
const ROWS = [
  { label: "Purpose", serving: "Primary CKD screening", legacy: "Legacy /v1 compatibility" },
  { label: "Algorithm", serving: MODEL_ALGORITHM, legacy: "MLP (ReLU)" },
  { label: "Training cohort", serving: "NHANES 2021-2023 (unweighted)", legacy: "UCI CKD (400 records)" },
  { label: "Features", serving: `${FEATURE_COUNT} native`, legacy: "24 (high missingness)" },
  { label: "Holdout ROC-AUC", serving: METRICS.rocAuc.toFixed(4), legacy: "0.5479" },
  { label: "Holdout PR-AUC", serving: METRICS.prAuc.toFixed(4), legacy: "not reported" },
  { label: "Recall / precision", serving: `${METRICS.recall.toFixed(3)} / ${METRICS.precision.toFixed(3)}`, legacy: "not reported" },
  { label: "Decision threshold", serving: DECISION_THRESHOLD.toFixed(3), legacy: "0.500 (default)" },
  { label: "Route", serving: "/v2/predict", legacy: "/predict, /predict/batch" },
];

export function ModelComparison() {
  return (
    <ClinicalShell title="Version comparison" subtitle={`Serving v${MODEL_VERSION} against the legacy model`}>
      <div className="mx-auto max-w-5xl space-y-5">
        <Alert tone="warning" title="Documented comparison, not a live one">
          The model registry endpoints this page used to call (<span className="font-mono">/api/v1/models</span>,
          <span className="font-mono"> /compare</span>, <span className="font-mono">/promote</span>) return 500 on this
          deployment. The values below come from the verified MLflow run and legacy model documentation.
        </Alert>

        <Card>
          <CardHeader
            icon={Info}
            title="Model generations"
            description="v15 is the only model pinned for serving; v9 stays reachable only on /v1."
            actions={
              <div className="flex gap-2">
                <Badge tone="low" dot>v{MODEL_VERSION} serving</Badge>
                <Badge tone="neutral">v9 legacy</Badge>
              </div>
            }
          />
          <div className="px-5 py-4">
            <Table minWidth={620}>
              <THead>
                <tr>
                  <TH>Attribute</TH>
                  <TH>Cohort model v{MODEL_VERSION}</TH>
                  <TH>Legacy v9</TH>
                </tr>
              </THead>
              <TBody>
                {ROWS.map((row) => (
                  <tr key={row.label}>
                    <TD className="text-on-surface-variant">{row.label}</TD>
                    <TD className="font-medium">{row.serving}</TD>
                    <TD className="text-on-surface-variant">{row.legacy}</TD>
                  </tr>
                ))}
              </TBody>
            </Table>
          </div>
          <p className="border-t border-outline-variant bg-surface-low px-5 py-3 text-xs leading-relaxed text-on-surface-variant">
            Metrics are not directly comparable: the two models were trained on different cohorts with different
            feature sets, so the gap reflects the data as much as the algorithm.
          </p>
        </Card>

        <Button as={Link} to="/models" variant="secondary" size="sm">
          Back to model performance
        </Button>
      </div>
    </ClinicalShell>
  );
}
