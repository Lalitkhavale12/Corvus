// NHANES-native schema accepted by POST /v2/predict (model v11).
// 16 numeric + 5 categorical = 21 fields. Blank numeric -> null (server-side imputer).
export const NHANES_GROUPS = [
  {
    title: "Demographics",
    fields: [
      { key: "RIDAGEYR", label: "Age", unit: "years" },
      { key: "INDFMPIR", label: "Income-to-poverty ratio" },
      {
        key: "RIAGENDR",
        label: "Sex",
        options: [
          ["1", "Male"],
          ["2", "Female"],
        ],
      },
      {
        key: "RIDRETH1",
        label: "Race / ethnicity",
        options: [
          ["1", "Mexican American"],
          ["2", "Other Hispanic"],
          ["3", "White"],
          ["4", "Black"],
          ["5", "Other"],
        ],
      },
      {
        key: "DMDEDUC2",
        label: "Education",
        options: [
          ["1", "< 9th grade"],
          ["2", "9–11th grade"],
          ["3", "HS grad / GED"],
          ["4", "Some college / AA"],
          ["5", "College grad"],
          ["9", "Missing"],
        ],
      },
      {
        key: "DIQ010",
        label: "Diagnosed diabetes",
        options: [
          ["1", "Yes"],
          ["2", "No"],
          ["3", "Borderline"],
        ],
      },
      {
        key: "MCQ035",
        label: "Ever told of kidney failure",
        options: [
          ["1", "Yes"],
          ["2", "No"],
          ["9", "Don't know"],
        ],
      },
    ],
  },
  {
    title: "Vitals",
    fields: [
      { key: "BMXBMI", label: "BMI", unit: "kg/m²" },
      { key: "BPXOSY1", label: "Systolic BP", unit: "mmHg" },
      { key: "BPXODI1", label: "Diastolic BP", unit: "mmHg" },
    ],
  },
  {
    title: "Blood chemistry",
    fields: [
      { key: "LBDSBUSI", label: "Blood urea nitrogen", unit: "mg/dL" },
      { key: "LBDSGLSI", label: "Glucose", unit: "mmol/L" },
      { key: "LBXSNASI", label: "Sodium", unit: "mmol/L" },
      { key: "LBXSKSI", label: "Potassium", unit: "mmol/L" },
      { key: "LBDSCASI", label: "Calcium", unit: "mmol/L" },
      { key: "LBDSPHSI", label: "Phosphorus", unit: "mmol/L" },
      { key: "LBXSAL", label: "Albumin", unit: "g/dL" },
      { key: "LBDSUASI", label: "Uric acid", unit: "mg/dL" },
      { key: "LBXSGTSI", label: "SGPT (ALT)", unit: "U/L" },
    ],
  },
  {
    title: "Hematology",
    fields: [
      { key: "LBXHGB", label: "Hemoglobin", unit: "g/dL" },
      { key: "LBXHCT", label: "Hematocrit", unit: "%" },
      { key: "LBXWBCSI", label: "WBC", unit: "10³/µL" },
      { key: "LBXRBCSI", label: "RBC", unit: "10⁶/µL" },
      { key: "LBXGH", label: "Glycohemoglobin", unit: "%" },
      { key: "LBXRDW", label: "RDW", unit: "%" },
    ],
  },
];

export const NHANES_FIELDS = NHANES_GROUPS.flatMap((g) => g.fields);

export function emptyNhanes() {
  return Object.fromEntries(NHANES_FIELDS.map((f) => [f.key, ""]));
}

export function toNhanesPayload(values) {
  const payload = {};
  for (const field of NHANES_FIELDS) {
    const raw = (values[field.key] ?? "").toString().trim();
    if (raw === "") {
      payload[field.key] = null;
    } else if (field.options) {
      // Coded categoricals are validated as integers (Literal[1, 2]) by the API,
      // so "1" must go over the wire as 1.
      const code = Number(raw);
      payload[field.key] = Number.isFinite(code) ? code : raw;
    } else {
      const num = Number(raw);
      payload[field.key] = Number.isFinite(num) ? num : null;
    }
  }
  return payload;
}
