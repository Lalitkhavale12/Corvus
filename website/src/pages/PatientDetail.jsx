import { useState } from "react";
import { PlaySquare, Share2, FileText, Cpu, ShieldCheck, Database } from "lucide-react";
import { useParams } from "react-router-dom";
import { ClinicalShell } from "../components/ClinicalShell";
import { Badge, Button, Card, Field, Input, ResultBadge, StatCard, StatusPill } from "../components/ui";
import { ROSTER_BY_ID, historyFor, EGFR_SERIES } from "../data/sample";
import { NhanesForm } from "../components/NhanesForm";
import { predictionAPI } from "../api";

function DrawCurve({ points, width = 620, height = 180 }) {
  const maxY = Math.max(...points.map((p) => p.y));
  const yScale = height / maxY;
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${height - p.y * yScale}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label="eGFR trajectory">
      <rect fill="#ECFDF5" opacity="0.5" width={width - 60} height={height * 0.45} x={30} y={height * 0.5} />
      <rect fill="#FFFBEB" opacity="0.5" width={width - 60} height={height * 0.25} x={30} y={height * 0.75} />
      <rect fill="#FEF2F2" opacity="0.5" width={width - 60} height={height * 0.3} x={30} y={height * 0.9} />
      <path d="M30,{height} L{width - 20},{height} M30,{height * 0.5} L{width - 20},{height * 0.5}" stroke="#CBD5E1" strokeWidth={1} />
      <path d={path} fill="none" stroke="#00288e" strokeWidth={2.5} />
      {points.map((p, i) => {
        const px = p.x;
        const py = height - p.y * yScale;
        const isCurrent = i === points.length - 1;
        const isDeclined = p.value < 60;
        return (
          <g key={i}>
            <circle cx={px} cy={py} r={isCurrent ? 5 : 4.5} fill={isDeclined ? "#DC2626" : "#00288e"} stroke="#fff" strokeWidth={2} />
            <text x={px} y={py - 7} textAnchor="middle" fontSize="10" fontWeight="700" fill="#0b1c30">
              {p.value}
            </text>
            <text x={px} y={height + 14} textAnchor="middle" fontSize="9" fill="#64748B">
              {p.label}
            </text>
          </g>
        );
      })}
      <text x={22} y={24} textAnchor="end" fontSize="9" fill="#64748B">80</text>
      <text x={22} y={height - 110} textAnchor="end" fontSize="9" fill="#64748B">60</text>
      <text x={22} y={height - 26} textAnchor="end" fontSize="9" fill="#DC262D" fontWeight="700">45</text>
    </svg>
  );
}

export function PatientDetail() {
  const { patientId } = useParams();
  const patient = ROSTER_BY_ID[patientId];
  const [openDrawer, setOpenDrawer] = useState(false);

  const savePrediction = async (payload) => {
    try {
      const _res = await predictionAPI.predict(payload);
      setOpenDrawer(false);
    } catch {
      // Prediction failed; drawer stays open for retry
    }
  };

  if (!patient) {
    return (
      <ClinicalShell title="Patient Not Found" actions={<></>}>
        <EmptyNotice />
      </ClinicalShell>
    );
  }

  const history = historyFor(patient.id);
  const latest = history[0];

  const predicateRow = ({ label, value, unit, tone = "neutral", note }) => (
    <Card className="p-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">{label}</p>
      <div className="flex items-baseline gap-1 mt-1">
        <span className={`text-xl font-bold tabular ${tone === "error" ? "text-tertiary" : "text-on-surface"}`}>
          {value}
        </span>
        {unit && <span className="text-xs text-on-surface-variant">{unit}</span>}
      </div>
      {note && <p className="mt-0.5 text-[11px] text-on-surface-variant">{note}</p>}
    </Card>
  );

  return (
    <ClinicalShell
      title={patient.name}
      subtitle={`${patient.mrn} • ${patient.age}y {patient.sex} • ${patient.conditions}`}
      actions={
        <>
          <Button variant="secondary" size="sm" asChild>
            <a href={`/doctor-dashboard`}>← Roster</a>
          </Button>
          <Button size="sm" onClick={() => setOpenDrawer(true)}>
            <PlaySquare className="size-3.5" /> Run New Prediction (/v2/predict)
          </Button>
          <Button variant="secondary" size="sm">
            <FileText className="size-3.5" />
          </Button>
          <Button variant="secondary" size="sm">
            <Share2 className="size-3.5" />
          </Button>
        </>
      }
    >
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <StatCard label="Latest result" value={latest ? (latest.probability * 100).toFixed(1) : "—"} hint="CKD probability" tone="high" />
          <StatCard label="Decision" value={latest ? (latest.prediction === 1 ? "CKD Detected" : "No CKD") : "—"} hint={latest ? latest.modelVersion : "no runs"} />
          <StatCard label="eGFR" value={patient.biomarkers?.egfr ?? "—"} hint="CKD-EPI mL/min/1.73m²" tone="error" />
          <StatCard label="uACR" value={patient.biomarkers?.uacr ?? "—"} hint="mg/g • A2" tone="moderate" />
        </div>

        <Card>
          <div className="flex flex-wrap justify-between items-start gap-4 border-b border-outline-variant px-5 py-4 sm:flex-row sm:items-center">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded border border-outline-variant bg-surface-low text-on-surface-variant">
                {patient.name.split(" ").map((w) => w[0]).join("")}
              </span>
              <div>
                <h2 className="text-base font-bold text-on-surface">{patient.name}</h2>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <span className="inline-block h-1 w-1 rounded-full bg-outline" />
                  <Badge tone={patient.prediction === 1 ? "high" : patient.prediction === 0 ? "low" : "neutral"} dot={false}>
                    {patient.prediction === null ? "Pending Labs" : patient.prediction === 1 ? "High Progression Risk" : "Stable"}
                  </Badge>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-2 sm:mt-0">
              <span className="font-data-metric text-data-metric text-on-surface">{patient.biomarkers?.egfr} mL</span>
              <span className="text-xs text-on-surface-variant">eGFR</span>
              <span className="font-data-metric text-data-metric text-on-surface">{patient.biomarkers?.creatinine} mg</span>
              <span className="text-xs text-on-surface-variant">creatinine</span>
            </div>
          </div>
          <div className="grid gap-3 p-5 lg:grid-cols-4">
            {predicateRow({ label: "eGFR (CKD-EPI)", value: patient.biomarkers?.egfr, unit: "mL/min/1.73m²", tone: "error", note: "Stage G3b (Moderate)" })}
            {predicateRow({ label: "Serum Creatinine", value: patient.biomarkers?.creatinine, unit: "mg/dL", tone: "error", note: "+0.3 from Jul 2026" })}
            {predicateRow({ label: "uACR", value: patient.biomarkers?.uacr, unit: "mg/g", tone: "moderate", note: "Stage A2 (Microalbumin)" })}
            {predicateRow({ label: "Systolic BP", value: patient.biomarkers?.sbp, unit: "mmHg", tone: "error", note: "Elevated vs target" })}
          </div>
          <div className="px-5 py-2 border-t border-outline-variant bg-surface-low">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant mb-2">Top attribution factors</p>
            <div className="flex flex-wrap gap-2">
              {["eGFR Δ (−7 mL)", "Systolic BP (142 mmHg)", "Age (62)", "T2D Comorbidity"].map((t) => (
                <Badge key={t} tone="neutral" dot={false}>
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="col-span-1 lg:col-span-2">
            <div className="border-b border-outline-variant p-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#DC2626]" />
              <h2 className="text-base font-bold text-on-surface">Latest Clinical Inference</h2>
              <span className="ml-auto text-[10px] text-on-surface-variant flex items-center gap-1">
                <ShieldCheck className="size-3" /> Verified
              </span>
            </div>
            <div className="flex items-baseline gap-1 mt-2 px-4">
              <Badge tone={latest?.prediction === 1 ? "high" : "low"}>
                {latest?.prediction === 1 ? "CKD Detected" : "No CKD Detected"}
              </Badge>
              <span className="text-2xl font-bold tabular text-on-surface">{latest ? fmtP(latest.probability) : "—"}</span>
              <span className="text-sm text-on-surface-variant">95% CI [0.84 – 0.93]</span>
            </div>
            <div className="mt-4 px-4">
              <div className="flex justify-between text-[10px] text-on-surface-variant mb-1">
                <span>Decision cutoff: 0.50</span>
                <span>Model: v11 NHANES Native</span>
              </div>
              <div className="h-3 w-full overflow-hidden rounded-full bg-surface-container relative">
                <div className="absolute top-0 bottom-0 left-[50%] w-0.5 bg-[#0b1c30] z-10" />
                <div
                  className={`h-full rounded-full ${latest ? (latest.prediction === 1 ? "bg-[#DC2626]" : "bg-[#059669]") : "animate-pulse bg-surface-container"}`}
                  style={{ width: latest ? `${Math.max(4, Math.round(latest.probability * 100))}%` : "20%" }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-on-surface-variant">
                <span>0.0 Negative</span>
                <span className="font-medium">{latest ? fmtP(latest.probability) : "—"}</span>
                <span>1.0 Positive</span>
              </div>
            </div>
            <Card className="mt-4 p-3 border-[#FECACA] bg-[#FEF2F2]">
              <div className="flex items-start gap-2">
                <Cpu className="mt-0.5 size-4 text-[#DC2626]" />
                <div className="space-y-1">
                  <p className="text-[11px] font-bold text-[#991B1B]">Clinical Recommendation Alert</p>
                  <p className="text-[12px] text-[#991B1B] leading-relaxed">
                    Action Recommended: Nephrology follow-up within 14 days. Consider SGLT2 inhibitor review. Repeat uACR &amp; renal panel in 90 days.
                  </p>
                </div>
              </div>
            </Card>
          </Card>

          <Card>
            <div className="border-b border-outline-variant p-4">
              <h2 className="text-base font-bold text-on-surface">eGFR Trajectory</h2>
              <p className="mt-1 text-[11px] text-on-surface-variant">
                Annualized decline −14.4 mL/min/1.73m²/yr. Accelerated decline Jan–Oct 2026.
              </p>
            </div>
            <div className="p-4">
              <DrawCurve points={EGFR_SERIES} />
            </div>
            <div className="px-4 py-3 border-t border-outline-variant flex justify-between text-[11px] text-on-surface-variant">
              <span>Observed eGFR</span>
              <span>KDIGO stage threshold (45)</span>
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="col-span-1 lg:col-span-2">
            <div className="border-b border-outline-variant p-4 flex items-center justify-between">
              <h2 className="text-base font-bold text-on-surface">Prediction History</h2>
              <span className="inline-flex items-center gap-1 rounded border border-outline-variant px-2 py-0.5 text-[10px] font-semibold text-on-surface-variant">
                {history.length} runs
              </span>
            </div>
            <div className="scrollbar-slim overflow-x-auto p-4">
              <table className="w-full min-w-[720px] text-left">
                <thead className="border-b border-outline-variant">
                  <tr className="text-[10px] uppercase tracking-wider text-on-surface-variant">
                    {["Run ID / Timestamp", "Model", "Risk", "Probability", "eGFR / Cr", "Evaluated By", "Status", ""].map((h) => (
                      <th key={h} className="px-3 py-2 font-semibold text-left">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {history.map((r) => (
                    <tr key={r.run} className={r.status === "verified" ? "bg-[#EFF6FF] border-l-2 border-primary" : ""}>
                      <td className="px-3 py-2 text-[11px] font-semibold text-on-surface tabular">{r.run}</td>
                      <td className="px-3 py-2 text-[11px] tabular text-on-surface-variant">
                        <Badge tone="neutral" dot={false}>v{r.modelVersion}</Badge>
                      </td>
                      <td className="px-3 py-2">
                        <ResultBadge prediction={r.prediction} />
                      </td>
                      <td className="px-3 py-2 text-right text-[11px] tabular font-semibold text-on-surface">{fmtP(r.probability)}</td>
                      <td className="px-3 py-2 text-right text-[11px] tabular text-on-surface-variant">
                        {r.egfr} mL / {r.creatinine} mg
                      </td>
                      <td className="px-3 py-2 text-[11px] text-on-surface">{r.by}</td>
                      <td className="px-3 py-2">
                        <StatusPill status={r.status} />
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Database className="size-3.5 text-on-surface-variant hover:text-on-surface cursor-pointer" />
                      </td>
                    </tr>
                  ))}
                  {history.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-3 py-4 text-center text-xs text-on-surface-variant">
                        No historical inference runs.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <div className="border-b border-outline-variant p-4">
              <h2 className="text-base font-bold text-on-surface">Uploaded Health Submissions</h2>
              <p className="mt-1 text-[11px] text-on-surface-variant">OCR-parsed lab panels ingested to PostgreSQL.</p>
            </div>
            <div className="px-4 py-3 space-y-3">
              {[["Quest_Diagnostics_Comprehensive_Renal_Panel_Oct2026.pdf", "RUN-90812"], ["Labcorp_Metabolic_Panel_Jul2026.pdf", "RUN-84190"]].map(([file, run]) => (
                <Card key={file} className="p-2">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="size-4 text-primary-container" />
                    <p className="text-xs font-semibold truncate text-on-surface">{file}</p>
                  </div>
                  <p className="text-[11px] text-on-surface-variant">Attached to {run} • Ingested via HL7 pipe</p>
                  <Badge tone="low" dot={false}>Parsed OK</Badge>
                </Card>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {openDrawer && (
        <div className="fixed inset-0 z-50 flex items-center justify-end p-4">
          <div className="absolute inset-0 bg-[#0b1c30]/50 backdrop-blur-sm" onClick={() => setOpenDrawer(false)} />
          <Card className="w-full max-w-md h-full flex flex-col shadow-2xl overflow-hidden sm:rounded-xl">
            <div className="border-b border-outline-variant px-5 py-4 flex items-center justify-between bg-surface-low">
              <div className="flex items-center gap-2">
                <span className="flex size-6 items-center justify-center rounded bg-primary-container text-on-primary">
                  <Database className="size-3.5" />
                </span>
                <h3 className="text-base font-bold text-on-surface">Run New Prediction</h3>
              </div>
              <button onClick={() => setOpenDrawer(false)} className="rounded p-1 text-on-surface-variant hover:bg-surface-low" aria-label="Close">
                <svg className="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-5 space-y-4">
              <Field label="Target Patient" htmlFor="target-patient">
                <Input id="target-patient" value={`${patient.name} (${patient.mrn})`} disabled />
              </Field>
              <NhanesForm onSubmit={savePrediction} submitLabel="Commit to PostgreSQL" />
            </div>
          </Card>
        </div>
      )}
    </ClinicalShell>
  );
}

function EmptyNotice() {
  return <div className="mt-20 px-6 text-center">Patient not found.</div>;
}

function fmtP(p) {
  return `${Number(p).toFixed(3)} (${(Number(p) * 100).toFixed(1)}%)`;
}
