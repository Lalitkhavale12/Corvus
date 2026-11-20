import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FlaskConical, Info, UserX } from "lucide-react";
import { ClinicalShell } from "../components/ClinicalShell";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, ResultBadge, Skeleton, StatCard, StatusPill, Table, TBody, TD, TH, THead } from "../components/ui";
import { ROSTER_BY_ID, EGFR_SERIES, historyFor } from "../data/sample";
import { predictionAPI } from "../api";

const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

function EgfrChart({ points }) {
  const width = 520;
  const height = 150;
  const padL = 28;
  const padR = 12;
  const padT = 16;
  const padB = 24;
  const values = points.map((p) => p.value);
  const min = Math.min(...values) - 8;
  const max = Math.max(...values) + 8;
  const x = (i) => padL + (i * (width - padL - padR)) / Math.max(1, points.length - 1);
  const y = (v) => padT + (1 - (v - min) / (max - min)) * (height - padT - padB);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-40 w-full" role="img" aria-label="eGFR series for the sample record">
      <line x1={padL} y1={y(60)} x2={width - padR} y2={y(60)} stroke="#E3E3DF" strokeDasharray="4 4" />
      <text x={padL - 6} y={y(60) + 4} textAnchor="end" fontSize="12" fill="#5A6068">60</text>
      <path d={path} fill="none" stroke="#0E7490" strokeWidth="2" strokeLinecap="round" />
      {points.map((p, i) => (
        <g key={p.label}>
          <circle cx={x(i)} cy={y(p.value)} r="4" fill="#0E7490" stroke="#FFFFFF" strokeWidth="2" />
          <text x={x(i)} y={y(p.value) - 10} textAnchor="middle" fontSize="12" fill="#17191C" fontWeight="600">
            {p.value}
          </text>
          <text x={x(i)} y={height - 6} textAnchor="middle" fontSize="12" fill="#5A6068">
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

function SampleRecord({ patient }) {
  const history = historyFor(patient.id);
  const latest = history[0];

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <Alert tone="warning" title="Illustrative preview — sample record">
        This record is invented to show the intended layout. It is not a real patient, and none of these numbers came
        from the serving model.
      </Alert>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Latest probability" value={latest ? latest.probability.toFixed(3) : "—"} hint="Sample value" />
        <StatCard label="Decision" value={latest?.prediction === 1 ? "CKD indicated" : latest ? "No CKD" : "—"} hint="Sample value" />
        <StatCard label="eGFR" value={patient.biomarkers?.egfr ?? "—"} hint="mL/min/1.73m²" />
        <StatCard label="uACR" value={patient.biomarkers?.uacr ?? "—"} hint="mg/g" />
      </div>

      <Card>
        <CardHeader
          icon={Info}
          title={`${patient.name} · ${patient.mrn}`}
          description={`${patient.age}yo ${patient.sex} · ${patient.conditions}`}
          actions={
            <Badge tone={patient.prediction === 1 ? "high" : patient.prediction === 0 ? "low" : "neutral"} dot>
              {patient.prediction === null ? "Labs pending" : patient.prediction === 1 ? "Flagged" : "Not flagged"}
            </Badge>
          }
        />
        <dl className="grid grid-cols-2 gap-4 p-5 lg:grid-cols-4">
          {[
            ["eGFR (CKD-EPI)", patient.biomarkers?.egfr, "mL/min/1.73m²"],
            ["Serum creatinine", patient.biomarkers?.creatinine, "mg/dL"],
            ["uACR", patient.biomarkers?.uacr, "mg/g"],
            ["Systolic BP", patient.biomarkers?.sbp, "mmHg"],
          ].map(([label, value, unit]) => (
            <div key={label}>
              <dt className="text-xs font-medium text-on-surface-variant">{label}</dt>
              <dd className="mt-0.5 flex items-baseline gap-1">
                <span className="font-mono text-xl font-semibold tabular text-on-surface">{value ?? "—"}</span>
                <span className="text-xs text-on-surface-variant">{unit}</span>
              </dd>
            </div>
          ))}
        </dl>
      </Card>

      <div className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader icon={Info} title="Sample run history" description={`${history.length} invented runs`} />
          {history.length === 0 ? (
            <EmptyState title="No runs in this sample" body="This sample patient has no prediction history." />
          ) : (
            <div className="px-5 py-4">
              <Table minWidth={560}>
                <THead>
                  <tr>
                    <TH>Run</TH>
                    <TH>When</TH>
                    <TH>Result</TH>
                    <TH className="text-right">Probability</TH>
                    <TH>Status</TH>
                  </tr>
                </THead>
                <TBody>
                  {history.map((run) => (
                    <tr key={run.run}>
                      <TD>
                        <span className="font-mono tabular">{run.run}</span>
                        <span className="ml-2 text-xs text-on-surface-variant">v{run.modelVersion}</span>
                      </TD>
                      <TD className="tabular text-on-surface-variant">{run.at}</TD>
                      <TD><ResultBadge prediction={run.prediction} /></TD>
                      <TD className="text-right font-mono tabular">{run.probability.toFixed(3)}</TD>
                      <TD><StatusPill status={run.status} /></TD>
                    </tr>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader icon={Info} title="eGFR series" description="Invented values for layout preview only." />
          <div className="p-4">
            <EgfrChart points={EGFR_SERIES} />
            <p className="mt-2 text-xs text-on-surface-variant">Dashed line marks the KDIGO 60 mL/min/1.73m² boundary.</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

function RealAssignment({ assignment }) {
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Patient id" value={`#${assignment.patient_id}`} hint="From the assignment record" />
        <StatCard label="Assignment" value={assignment.is_active ? "Active" : "Inactive"} hint={assignment.is_active ? "is_active = true" : "Assignment revoked"} />
        <StatCard label="Assigned" value={assignment.assigned_at ? dateFmt.format(new Date(assignment.assigned_at)) : "—"} />
      </div>

      <Card>
        <CardHeader
          icon={UserX}
          title="No clinical data available"
          description="The assignment API returns the doctor-patient link only."
        />
        <div className="space-y-3 p-5 text-sm leading-relaxed text-on-surface-variant">
          <p>
            There is no per-patient prediction or results endpoint in this build, so this page cannot show labs,
            history, or risk for patient #{assignment.patient_id}.
          </p>
          <p>
            To produce a risk estimate, run an assessment on the dashboard. The result is stored against your own
            account and appears in your prediction history — it is not attributed to this patient id.
          </p>
          <Button as={Link} to="/dashboard" size="sm">Open the assessment form</Button>
        </div>
      </Card>
    </div>
  );
}

export function PatientDetail() {
  const { patientId } = useParams();
  const sample = ROSTER_BY_ID[patientId];
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(!sample);
  const [error, setError] = useState("");

  useEffect(() => {
    if (sample) return;
    predictionAPI
      .getDoctorPatients()
      .then((res) => {
        const match = (res.data || []).find((row) => String(row.patient_id) === String(patientId));
        setAssignment(match ?? null);
      })
      .catch(() => setError("Could not load the assignment record."))
      .finally(() => setLoading(false));
  }, [patientId, sample]);

  const back = (
    <Button as={Link} to="/doctor-dashboard" variant="secondary" size="sm">
      <ArrowLeft className="size-4" aria-hidden="true" />
      Roster
    </Button>
  );

  if (sample) {
    return (
      <ClinicalShell
        title={sample.name}
        subtitle={`${sample.mrn} · sample record`}
        actions={
          <>
            {back}
            <Badge tone="moderate" dot>
              <FlaskConical className="mr-1 size-3.5" aria-hidden="true" />
              Sample data
            </Badge>
          </>
        }
      >
        <SampleRecord patient={sample} />
      </ClinicalShell>
    );
  }

  return (
    <ClinicalShell title={`Patient #${patientId}`} subtitle="Assignment record" actions={back}>
      {loading ? (
        <div className="mx-auto max-w-3xl space-y-4">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : error ? (
        <div className="mx-auto max-w-3xl">
          <Alert tone="danger" title="Patient unavailable">{error}</Alert>
        </div>
      ) : assignment ? (
        <RealAssignment assignment={assignment} />
      ) : (
        <div className="mx-auto max-w-3xl">
          <EmptyState
            icon={UserX}
            title={`No assignment for patient #${patientId}`}
            body="This patient id is not on your roster, so there is nothing to display."
            action={
              <Button as={Link} to="/assign-patients" size="sm">
                Assign a patient
              </Button>
            }
          />
        </div>
      )}
    </ClinicalShell>
  );
}
