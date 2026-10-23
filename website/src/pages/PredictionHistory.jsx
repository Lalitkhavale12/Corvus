import { useAuth } from "../contexts/AuthContext";

export function PredictionHistory() {
  const { user } = useAuth();

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Prediction History
      </h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">
          Hello, {user?.email.split("@")[0]}
        </h2>
        <p className="text-gray-600 mb-4">
          View your past CKD prediction results.
        </p>

        <div className="text-gray-500 text-sm">
          No predictions yet. Visit the Prediction page to get your first assessment.
        </div>
      </div>
    </div>
  );
}
