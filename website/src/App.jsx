import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ClinicalLogin } from "./pages/ClinicalLogin";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { DoctorDashboard } from "./pages/DoctorDashboard";
import { PatientDetail } from "./pages/PatientDetail";
import { PredictionHistory } from "./pages/PredictionHistory";
import { Models } from "./pages/Models";
import { PatientProfile } from "./pages/PatientProfile";
import { DoctorProfile } from "./pages/DoctorProfile";
import { AssignPatients } from "./pages/AssignPatients";
import { ModelComparison } from "./pages/ModelComparison";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RoleGate({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) {
    return <Navigate to={user.role === "doctor" ? "/doctor-dashboard" : "/dashboard"} replace />;
  }
  return children;
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "doctor" ? "/doctor-dashboard" : "/dashboard"} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<ClinicalLogin />} />
        <Route path="/register" element={<Register />} />

        <Route
          path="/dashboard"
          element={
            <RoleGate role="patient">
              <Dashboard />
            </RoleGate>
          }
        />
        <Route
          path="/history"
          element={
            <RoleGate role="patient">
              <PredictionHistory />
            </RoleGate>
          }
        />
        <Route
          path="/doctor-dashboard"
          element={
            <RoleGate role="doctor">
              <DoctorDashboard />
            </RoleGate>
          }
        />
        <Route
          path="/patients/:patientId"
          element={
            <RoleGate role="doctor">
              <PatientDetail />
            </RoleGate>
          }
        />
        <Route
          path="/models"
          element={
            <Protected>
              <Models />
            </Protected>
          }
        />
        <Route
          path="/profile"
          element={
            <Protected>
              <PatientProfile />
            </Protected>
          }
        />
        <Route
          path="/doctor-profile"
          element={
            <RoleGate role="doctor">
              <DoctorProfile />
            </RoleGate>
          }
        />
        <Route
          path="/assign-patients"
          element={
            <RoleGate role="doctor">
              <AssignPatients />
            </RoleGate>
          }
        />
        <Route
          path="/models/model-comparison"
          element={
            <Protected>
              <ModelComparison />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
