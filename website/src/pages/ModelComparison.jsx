import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { predictionAPI } from "../api";
import { ClinicalShell } from "../components/ClinicalShell";
import { Button, Card, Field, Input, Spinner } from "../components/ui";

export function ModelComparison() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [models, setModels] = useState([]);
  const [championVersion, setChampionVersion] = useState("9");
  const [challengerVersion, setChallengerVersion] = useState("11");
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const modelsRes = await fetchModelsList();
      setModels(modelsRes.models || []);
    } catch (err) {
      setError("Failed to load models");
    } finally {
      setLoading(false);
    }
  };

  const fetchModelsList = async () => {
    try {
      const res = await fetch(`${predictionAPI.baseURL}/api/v1/models`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      if (!res.ok) throw new Error("Failed to fetch models");
      return await res.json();
    } catch (err) {
      setError("Failed to load models");
      return { models: [] };
    }
  };

  const compareModels = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${predictionAPI.baseURL}/api/v1/models/compare?champion_version=${championVersion}&challenger_version=${challengerVersion}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );
      if (!res.ok) throw new Error("Comparison failed");
      const data = await res.json();
      setComparison(data);
    } catch (err) {
      setError("Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const promoteChallenger = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${predictionAPI.baseURL}/api/v1/models/promote?challenger_version=${challengerVersion}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );
      if (!res.ok) throw new Error("Promotion failed");
      const data = await res.json();
      if (data.promoted) {
        setComparison(data);
        setLoading(false);
        navigate("/models/model-comparison");
      } else {
        setError(data.reason || "Promotion failed");
        setLoading(false);
      }
    } catch (err) {
      setError("Promotion failed");
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="animate-pulse rounded bg-surface-container h-8 w-1/3 mx-auto" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col bg-surface">
        <ClinicalShell title="Model Comparison" actions={<></>}>
          <div className="mx-auto max-w-md py-12">
            <div className="rounded border border-[#FECACA] bg-[#FEF2F2] p-6">
              <h2 className="text-lg font-bold text-[#991B1B]">Error</h2>
              <p className="mt-1 text-sm text-[#991B1B]">{error}</p>
              <Button onClick={() => window.location.reload()} variant="secondary">
                Retry
              </Button>
            </div>
          </div>
        </ClinicalShell>
      </div>
    );
  }

  return (
    <ClinicalShell
      title="Model Comparison"
      subtitle={`Compare ${championVersion} (champion) vs ${challengerVersion} (challenger)`}
      actions={
        <>
          <Button variant="secondary" onClick={fetchModels} disabled={loading}>
            <RefreshCw className="size-3.5" /> Refresh
          </Button>
          {comparison && comparison.is_better && (
            <Button onClick={promoteChallenger} disabled={loading}>
              <TrendingUp className="size-3.5" /> Promote Challenger
            </Button>
          )}
        </>
      }
    >
      <div className="mx-auto max-w-5xl space-y-5">
        <Card className="p-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-on-surface-variant">Champion:</span>
              <select
                value={championVersion}
                onChange={(e) => setChampionVersion(e.target.value)}
                className="border border-outline-variant rounded px-2 py-1 text-sm bg-surface-lowest"
              >
                {models.map((m) => (
                  <option key={m.version} value={m.version}>
                    v{m.version} ({m.stage})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-on-surface-variant">Challenger:</span>
              <select
                value={challengerVersion}
                onChange={(e) => setChallengerVersion(e.target.value)}
                className="border border-outline-variant rounded px-2 py-1 text-sm bg-surface-lowest"
              >
                {models.map((m) => (
                  <option key={m.version} value={m.version}>
                    v{m.version} ({m.stage})
                  </option>
                ))}
              </select>
            </div>
            <Button onClick={compareModels} disabled={loading}>
              {loading ? <RefreshCw className="size-3.5" /> : <ArrowRight className="size-3.5" />}
              {loading ? "Comparing..." : "Compare Models"}
            </Button>
          </div>
          {error && (
            <div className="mt-4 rounded border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#991B1B]">
              {error}
            </div>
          )}
        </Card>

        {comparison && (
          <>
            <Card className="p-6">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-outline-variant pb-4">
                <div>
                  <h2 className="text-lg font-bold text-on-surface">Comparison Results</h2>
                  <p className="text-sm text-on-surface-variant">
                    {comparison.improvements} improved &bull; {comparison.degradations} degraded
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {comparison.recommend_promote ? (
                    <span className="flex items-center gap-1 rounded bg-[#ECFDF5] px-2 py-1 text-[#065F46]">
                      <TrendingUp className="size-3.5" /> Recommended for promotion
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 rounded bg-[#FEF2F2] px-2 py-1 text-[#991B1B]">
                      Not recommended for promotion
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="p-4 border-[#00288e]/30 bg-[#E2E8F0]/50">
                  <h3 className="text-sm font-bold text-[#00288e] mb-3">
                    Champion v{comparison.champion_version}
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(comparison.champion_metrics).map(([key, val]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-on-surface-variant">{key}</span>
                        <span className="font-mono text-on-surface">
                          {typeof val === "number" ? val.toFixed(4) : val}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card className="p-4 border-[#006c4a]/30 bg-[#ECFDF5]/50">
                  <h3 className="text-sm font-bold text-[#006c4a] mb-3">
                    Challenger v{comparison.challenger_version}
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(comparison.challenger_metrics).map(([key, val]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-on-surface-variant">{key}</span>
                        <span className="font-mono text-on-surface">
                          {typeof val === "number" ? val.toFixed(4) : val}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </Card>
            </>
          )}
      </div>
    </ClinicalShell>
  );
}
