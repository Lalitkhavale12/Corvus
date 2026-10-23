import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { predictionAPI } from "../api";

const NHANES_NUMERIC = [
  "RIDAGEYR", "INDFMPIR", "LBDSBUSI", "LBDSGLSI", "LBXSNASI", "LBXSKSI",
  "LBDSCASI", "LBDSPHSI", "LBXHGB", "LBXHCT", "LBXWBCSI", "LBXRBCSI",
  "LBXGH", "BMXBMI", "BPXOSY1", "BPXODI1",
];

const NHANES_CATEGORICAL = {
  RIAGENDR: ["1 — Male", "2 — Female"],
  RIDRETH1: ["1 — Mexican American", "2 — Other Hispanic", "3 — White", "4 — Black", "5 — Other"],
  DMDEDUC2: ["1 — <9th grade", "2 — 9–11th grade", "3 — HS grad/GED", "4 — Some college/AA", "5 — College grad", "9 — Missing"],
  DIQ010: ["1 — Yes", "2 — No", "3 — Borderline"],
  MCQ035: ["1 — Yes", "2 — No", "9 — Don't know"],
};

export function Dashboard() {
  const { user } = useAuth();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePredict = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const numeric = {};
    NHANES_NUMERIC.forEach((field) => {
      const el = document.getElementById(field);
      const val = el?.value.trim();
      numeric[field] = val === "" ? null : parseFloat(val);
    });

    const categorical = {};
    Object.keys(NHANES_CATEGORICAL).forEach((field) => {
      const el = document.getElementById(field);
      const val = el?.value;
      categorical[field] = val ? val.split(" — ")[0] : null;
    });

    try {
      const res = await predictionAPI.predict({ ...numeric, ...categorical });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome, {user?.email.split("@")[0]}
        </h1>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
            Account active
          </span>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">CKD Risk Prediction</h2>
        <p className="text-gray-600 mb-6">
          Enter your NHANES health data to assess chronic kidney disease risk using our v11 GradientBoosting model.
        </p>

        <form onSubmit={handlePredict} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {NHANES_NUMERIC.map((field) => (
              <div key={field} className="space-y-2">
                <label className="text-sm font-medium text-gray-700">{field}</label>
                <input
                  id={field}
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="blank = missing"
                />
              </div>
            ))}
          </div>

          <div className="border-t pt-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Demographics & History</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(NHANES_CATEGORICAL).map(([field, options]) => (
                <div key={field} className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">{field}</label>
                  <select
                    id={field}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="">Select...</option>
                    {options.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {loading ? "Analyzing..." : "Get Prediction"}
          </button>
        </form>
      </div>

      {result && (
        <div className="mt-8 p-6 rounded-lg border border-indigo-200 bg-indigo-50">
          <h3 className="text-lg font-semibold text-indigo-900 mb-2">
            Prediction Result
          </h3>
          <div className="flex items-center gap-4">
            <div className="text-3xl font-bold">
              {result.prediction === 1 ? "CKD Detected" : "No CKD Detected"}
            </div>
            <div className="flex-1">
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className={`h-4 rounded-full ${
                    result.prediction === 1 ? "bg-red-500" : "bg-green-500"
                  }`}
                  style={{ width: `${Math.round(result.probability * 100)}%` }}
                ></div>
              </div>
              <div className="mt-1 text-sm text-gray-600">
                CKD Probability: {(result.probability * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-sm text-gray-600">
              Model: v{result.model_version}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
