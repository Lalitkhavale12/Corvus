import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { Navbar } from "./components/Navbar";
import { ProtectedRoute, PatientRoute, DoctorRoute } from "./components/ProtectedRoute";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { DoctorDashboard } from "./pages/DoctorDashboard";
import { PredictionHistory } from "./pages/PredictionHistory";

function App() {
  return (
    <Router>
      <AuthProvider>
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            element={<ProtectedRoute />}
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route
              path="/predict"
              element={
                <PatientRoute>
                  <Dashboard />
                </PatientRoute>
              }
            />
            <Route
              path="/history"
              element={
                <PatientRoute>
                  <PredictionHistory />
                </PatientRoute>
              }
            />
            <Route
              path="/doctor-dashboard"
              element={<DoctorDashboard />}
            />
          </Route>
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
