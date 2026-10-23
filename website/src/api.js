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
};

export default api;
