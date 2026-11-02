import { useEffect, useState } from "react";
import { Edit2, Save, User } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { authAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { Badge, Button, Card, Field, Input, Select, Spinner } from "../components/ui";

export function PatientProfile() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    sex: "",
    phone: "",
    mrn: "",
  });

  useEffect(() => {
    authAPI
      .getProfile()
      .then((res) => {
        setProfile(res.data);
        const p = res.data.patient_profile || {};
        setForm({
          first_name: p.first_name || "",
          last_name: p.last_name || "",
          sex: p.sex || "",
          phone: p.phone || "",
          mrn: p.mrn || "",
        });
      })
      .catch((err) => {
        if (err.response?.status === 404) {
          setProfile(null);
        } else {
          setError("Unable to load profile");
        }
      })
      .finally(() => setPageLoading(false));
  }, []);

  if (pageLoading) return <Spinner />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await authAPI.createProfile(form);
      setProfile({ role: "patient", patient_profile: form });
      setEditing(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save profile");
    }
  };

  if (!profile) {
    return (
      <ClinicalShell title="Create Profile" actions={<></>}>
        <Card className="w-full max-w-md mx-auto">
          <div className="px-6 py-6 border-b border-outline-variant">
            <h2 className="text-lg font-bold text-on-surface">Set up your patient profile</h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              Tell us a bit about yourself. This is linked to your account ({user?.email}).
            </p>
          </div>
          <form onSubmit={submit} className="px-6 py-6 space-y-4">
            <Field label="First Name" htmlFor="first_name">
              <Input id="first_name" required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </Field>
            <Field label="Last Name" htmlFor="last_name">
              <Input id="last_name" required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </Field>
            <Field label="MRN (Medical Record Number)" htmlFor="mrn" hint="Optional">
              <Input id="mrn" value={form.mrn} onChange={(e) => setForm({ ...form, mrn: e.target.value })} />
            </Field>
            <Field label="Sex" htmlFor="sex">
              <Select value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
                <option value="">Not specified</option>
                <option value="M">Male</option>
                <option value="F">Female</option>
                <option value="O">Other</option>
              </Select>
            </Field>
            <Field label="Phone" htmlFor="phone" hint="Optional">
              <Input id="phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </Field>
            {error && (
              <div className="rounded border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#991B1B]">
                {error}
              </div>
            )}
            <Button type="submit" size="lg" className="w-full">
              Save profile
            </Button>
          </form>
        </Card>
      </ClinicalShell>
    );
  }

  const p = profile.patient_profile;
  return (
    <ClinicalShell
      title="Patient Profile"
      subtitle={user?.email}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={() => setEditing(!editing)}>
            {editing ? <Save className="size-3.5" /> : <Edit2 className="size-3.5" />}
            {editing ? "Cancel" : "Edit"}
          </Button>
        </>
      }
    >
      {editing ? (
        <Card className="w-full max-w-md mx-auto">
          <div className="px-6 py-6 border-b border-outline-variant">
            <h2 className="text-lg font-bold text-on-surface">Edit profile</h2>
          </div>
          <form onSubmit={submit} className="px-6 py-6 space-y-4">
            <Field label="First Name" htmlFor="first_name">
              <Input id="first_name" required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </Field>
            <Field label="Last Name" htmlFor="last_name">
              <Input id="last_name" required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </Field>
            <Field label="MRN" htmlFor="mrn">
              <Input id="mrn" value={form.mrn} onChange={(e) => setForm({ ...form, mrn: e.target.value })} />
            </Field>
            <Button type="submit">Save changes</Button>{" "}
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <p className="mt-3 text-[11px] text-on-surface-variant">
              Note: a full update endpoint lands in Phase 8-03; save re-creates the profile.
            </p>
          </form>
        </Card>
      ) : (
        <Card className="w-full max-w-md mx-auto">
          <div className="px-6 py-6 border-b border-outline-variant flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-on-surface">{p.first_name} {p.last_name}</h2>
              <p className="mt-1 text-sm text-on-surface-variant">Patient profile</p>
            </div>
            <Badge tone="primary">Patient</Badge>
          </div>
          <div className="px-6 py-4 space-y-3">
            <div className="flex items-center gap-3 border-b border-outline-variant pb-3">
              <span className="flex size-6 items-center justify-center rounded bg-surface-low text-on-surface-variant">
                <User className="size-4" />
              </span>
              <div>
                <p className="text-sm font-semibold text-on-surface">MRN</p>
                <p className="text-[11px] text-on-surface-variant tabular">{p.mrn || "—"}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 border-b border-outline-variant pb-3">
              <span className="text-[11px] font-semibold text-on-surface-variant">Sex</span>
              <span className="ml-auto text-[11px] text-on-surface-variant tabular">{p.sex || "Not specified"}</span>
            </div>
            <div className="flex items-center gap-3 border-b border-outline-variant pb-3">
              <span className="text-[11px] font-semibold text-on-surface-variant">Phone</span>
              <span className="ml-auto text-[11px] text-on-surface-variant tabular">{p.phone || "—"}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-semibold text-on-surface-variant">Member since</span>
              <span className="ml-auto text-[11px] text-on-surface-variant tabular">
                {p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}
              </span>
            </div>
          </div>
          <div className="px-6 py-3 border-t border-outline-variant">
            <p className="text-[11px] text-on-surface-variant">
              Account email: <span className="font-semibold text-on-surface">{user?.email}</span>
            </p>
          </div>
        </Card>
      )}
    </ClinicalShell>
  );
}