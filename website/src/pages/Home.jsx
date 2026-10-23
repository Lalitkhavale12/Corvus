import { Link } from "react-router-dom";

export function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="font-bold text-xl text-indigo-600">
                  Corvus CKD
                </Link>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:items-center">
                <Link
                  to="/login"
                  className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="ml-4 px-3 py-2 rounded-md text-sm font-medium text-indigo-600 hover:bg-indigo-50"
                >
                  Sign up
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-12 sm:px-6 lg:px-8">
        <div className="bg-white overflow-hidden shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:px-6">
            <h1 className="text-3xl font-bold text-gray-900">
              Chronic Kidney Disease Risk Assessment
            </h1>
            <p className="mt-2 text-gray-600">
              A multi-user MLOps platform for CKD risk prediction. Register as a
              patient or doctor to get started.
            </p>
          </div>
          <div className="px-4 py-5 sm:px-6 sm:flex sm:flex-row-reverse">
            <div className="sm:w-1/2 sm:pl-6">
              <h2 className="text-xl font-medium text-gray-900 mb-4">
                For Patients
              </h2>
              <p className="text-gray-600 mb-4">
                Enter your NHANES health data to receive a CKD risk assessment
                powered by our machine learning model. View your prediction
                history anytime.
              </p>
              <Link
                to="/register"
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md hover:bg-indigo-700"
              >
                Sign up as a patient
              </Link>
            </div>
            <div className="mt-5 sm:mt-0 sm:w-1/2">
              <h2 className="text-xl font-medium text-gray-900 mb-4">
                For Doctors
              </h2>
              <p className="text-gray-600 mb-4">
                Register as a doctor to view your assigned patients' prediction
                results and monitor their CKD risk over time.
              </p>
              <Link
                to="/register"
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md hover:bg-indigo-700"
              >
                Sign up as a doctor
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
