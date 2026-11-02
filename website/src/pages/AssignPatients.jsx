import { useEffect, useState } from "react";
import { Plus, UserPlus } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { authAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { Badge, Button, Card, Field, Input, Spinner } from "../components/ui";

export function AssignPatients() {
  const { user } = useAuth();
  const [patients, setPatients] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    authAPI
      .getDoctorPatients()
      .then((res) => setPatients(res.data))
      .catch((err) => {
        if (err.response?.status === 403) {
          setError("Doctor role required");
        } else {
          setError("Unable to load patients");
        }
      })
      .finally(() => setPageLoading(false));
  }, []);

  const [assignEmail, setAssignEmail] = useState("");

  const assign = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await authAPI.assignPatient(assignEmail);
      setAssignEmail("");
      const updated = await authAPI.getDoctorPatients();
      setPatients(updated.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to assign patient");
    }
  };

  if (pageLoading) return <Spinner />;

  return (
    <ClinicalShell title="Assign Patients" subtitle={user?.email}>
      <Card className="w-full max-w-lg">
        <div className="px-6 py-6 border-b border-outline-variant">
          <h2 className="text-lg font-bold text-on-surface">Assign a patient</h2>
          <p className="mt-1 text-sm text-on-surface-variant">
            Enter the patient&rsquo;s registered email to add them to your patient list.
          </p>
        </div>
        <form onSubmit={assign} className="px-6 py-6 space-y-4">
          <Field label="Patient email" htmlFor="patient_email">
            <Input
              id="patient_email"
              type="email"
              required
              placeholder="patient@example.com"
              value={assignEmail}
              onChange={(e) => setAssignEmail(e.target.value)}
            />
          </Field>
          {error && (
            <div className="rounded border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#991B1B]">
              {error}
            </div>
          )}
          <Button type="submit" size="lg" className="w-full">
            <Plus className="size-3.5" /> Assign patient
          </Button>
        </form>
      </Card>

      <Card className="w-full max-w-lg mt-4">
        <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between">
          <h2 className="text-lg font-bold text-on-surface">Your patients</h2>
          <Badge tone="primary">{patients.length}</Badge>
        </div>
        <div className="px-6 py-4">
          {patients.length === 0 ? (
            <div className="text-center py-8 text-on-surface-variant text-sm">
              No patients assigned yet. Use the form above to add one.
            </div>
          ) : (
            <div className="space-y-2">
              {patients.map((m) => (
                <div key={m.id} className="flex items-center justify-between px-4 py-2 rounded border border-outline-variant bg-surface-low">
                  <div className="flex items-center gap-3">
                    <span className="flex size-6 items-center justify-center rounded bg-surface-lowest text-on-surface-variant">
                      <UserPlus className="size-3.5" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-on-surface">Patient #{m.patient_id}</p>
                      <p className="text-[11px] text-on-surface-variant">
                        Assigned {m.assigned_at ? new Date(m.assigned_at).toLocaleDateString() : "—"}
                      </p>
                    </div>
                  </div>
                  <Badge tone={m.is_active ? "low" : "neutral"} dot={false}>
                    {m.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </ClinicalShell>
  );
}
