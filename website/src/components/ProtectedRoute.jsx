import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  if (loading) return null;

  if (!user) {
    navigate("/login");
    return null;
  }

  return children;
}

export function PatientRoute({ children }) {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  if (loading) return null;

  if (!user || user.role !== "patient") {
    navigate("/login");
    return null;
  }

  return children;
}

export function DoctorRoute({ children }) {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  if (loading) return null;

  if (!user || user.role !== "doctor") {
    navigate("/login");
    return null;
  }

  return children;
}
