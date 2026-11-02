// ponytail: static roster until doctor→patient assignment ships (phase 8-03).
// Shapes mirror what GET /doctors/patients will return, so swapping in fetch is a
// one-function change in DoctorDashboard/PatientDetail.
export const ROSTER = [
  {
    id: "mrn-84920",
    name: "Maria Gonzalez",
    mrn: "MRN-84920",
    age: 62,
    sex: "F",
    conditions: "Type 2 Diabetes, Hypertension Stage 2",
    prediction: 1,
    probability: 0.892,
    modelVersion: "11",
    lastAt: "2026-10-20",
    status: "verified",
    biomarkers: { egfr: 44, creatinine: 1.8, uacr: 180, sbp: 142 },
  },
  {
    id: "mrn-33912",
    name: "James Chen",
    mrn: "MRN-33912",
    age: 48,
    sex: "M",
    conditions: "No recorded comorbidity",
    prediction: 0,
    probability: 0.145,
    modelVersion: "9",
    lastAt: "2026-10-18",
    status: "verified",
    biomarkers: { egfr: 78, creatinine: 1.1, uacr: 22, sbp: 118 },
  },
  {
    id: "mrn-77401",
    name: "Robert Davis",
    mrn: "MRN-77401",
    age: 71,
    sex: "M",
    conditions: "Hypertension, CKD Stage G3b",
    prediction: 1,
    probability: 0.671,
    modelVersion: "11",
    lastAt: "2026-10-19",
    status: "verified",
    biomarkers: { egfr: 51, creatinine: 1.5, uacr: 96, sbp: 136 },
  },
  {
    id: "mrn-21049",
    name: "Eleanor Vance",
    mrn: "MRN-21049",
    age: 54,
    sex: "F",
    conditions: "Obesity Class I",
    prediction: 0,
    probability: 0.082,
    modelVersion: "11",
    lastAt: "2026-10-15",
    status: "verified",
    biomarkers: { egfr: 82, creatinine: 0.9, uacr: 12, sbp: 124 },
  },
  {
    id: "mrn-90214",
    name: "Marcus Brody",
    mrn: "MRN-90214",
    age: 39,
    sex: "M",
    conditions: "Awaiting serum creatinine",
    prediction: null,
    probability: null,
    modelVersion: null,
    lastAt: "2026-10-14",
    status: "pending",
    biomarkers: null,
  },
];

export const ROSTER_BY_ID = Object.fromEntries(ROSTER.map((p) => [p.id, p]));

export function historyFor(patientId) {
  const runs = {
    "mrn-84920": [
      { run: "RUN-90812", at: "2026-10-20 09:42", prediction: 1, probability: 0.892, modelVersion: "11", egfr: 44, creatinine: 1.8, by: "Dr. Sarah Jenkins", status: "verified" },
      { run: "RUN-84190", at: "2026-07-14 14:15", prediction: 1, probability: 0.671, modelVersion: "11", egfr: 51, creatinine: 1.5, by: "Dr. Sarah Jenkins", status: "verified" },
      { run: "RUN-65201", at: "2026-01-10 11:30", prediction: 0, probability: 0.412, modelVersion: "9", egfr: 62, creatinine: 1.2, by: "Dr. Alex Wong", status: "archived" },
      { run: "RUN-42110", at: "2025-06-05 08:20", prediction: 0, probability: 0.145, modelVersion: "9", egfr: 68, creatinine: 1.1, by: "Dr. Alex Wong", status: "archived" },
    ],
    "mrn-77401": [
      { run: "RUN-91105", at: "2026-10-19 16:08", prediction: 1, probability: 0.671, modelVersion: "11", egfr: 51, creatinine: 1.5, by: "Dr. Sarah Jenkins", status: "verified" },
    ],
    "mrn-33912": [
      { run: "RUN-90477", at: "2026-10-18 10:22", prediction: 0, probability: 0.145, modelVersion: "9", egfr: 78, creatinine: 1.1, by: "Dr. Sarah Jenkins", status: "verified" },
    ],
    "mrn-21049": [
      { run: "RUN-89930", at: "2026-10-15 08:55", prediction: 0, probability: 0.082, modelVersion: "11", egfr: 82, creatinine: 0.9, by: "Dr. Sarah Jenkins", status: "verified" },
    ],
    "mrn-90214": [],
  };
  return runs[patientId] ?? [];
}

export const EGFR_SERIES = [
  { label: "Jun 2025", value: 68 },
  { label: "Jan 2026", value: 62 },
  { label: "Jul 2026", value: 51 },
  { label: "Oct 2026", value: 44 },
];
