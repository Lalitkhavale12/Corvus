import { useAuth } from "../contexts/AuthContext";

export function DoctorDashboard() {
  const { user } = useAuth();

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Doctor Dashboard
      </h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Welcome, Dr. {user?.email.split("@")[0]}</h2>
        <p className="text-gray-600 mb-4">
          View and manage your assigned patients' CKD predictions.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-indigo-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-indigo-900">Assigned Patients</h3>
            <p className="text-2xl font-bold text-indigo-600 mt-2">0</p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-blue-900">Pending Reviews</h3>
            <p className="text-2xl font-bold text-blue-600 mt-2">0</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-green-900">CKD Cases Flagged</h3>
            <p className="text-2xl font-bold text-green-600 mt-2">0</p>
          </div>
        </div>

        <div className="mt-8">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Patient List</h3>
          <p className="text-gray-500 text-sm">No patients assigned yet. Patients will appear here once they add you as their doctor.</p>
        </div>
      </div>
    </div>
  );
}
