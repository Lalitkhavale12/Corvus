import { useEffect, useState } from "react";
import { AuthContext } from "./authStore";
import { authAPI } from "../api";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem("token")));

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      authAPI
        .me()
        .then((res) => {
          setUser(res.data);
          // A 404 here just means no profile row yet; it must not log the user out.
          return authAPI.getProfile().then(
            (profile) => setUser((prev) => ({ ...prev, profile: profile.data })),
            () => {}
          );
        })
        .catch(() => {
          localStorage.removeItem("token");
          setUser(null);
        })
        .finally(() => setLoading(false));
    }
  }, []);

  const login = async (token) => {
    localStorage.setItem("token", token);
    const res = await authAPI.me();
    setUser(res.data);
    try {
      const profile = await authAPI.getProfile();
      setUser((prev) => ({ ...prev, profile: profile.data }));
    } catch {
      // No profile yet — user will be prompted to create one
    }
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
