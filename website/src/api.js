import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token to every request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
  // Phase 8-02: profile + patient-doctor mapping endpoints
  getProfile: () => api.get("/auth/profile"),
  createProfile: (data) => api.post("/auth/profile", data),
  getDoctorPatients: () => api.get("/doctors/patients"),
  assignPatient: (patientEmail) =>
    api.post("/doctors/patients/assign", { patient_email: patientEmail }),
};

export const predictionAPI = {
  predict: (data) => api.post("/v2/predict", data),
  batchPredict: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/v2/batch_predict", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  modelInfo: () => api.get("/v2/model_info"),
  health: () => api.get("/health"),
  // Phase 8-03: prediction history endpoints
  getHistory: () => api.get("/auth/predictions"),
  getPrediction: (id) => api.get(`/auth/predictions/${id}`),
};

export default api;
