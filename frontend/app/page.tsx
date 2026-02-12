"use client";

import { useState } from "react";

export default function Home() {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const handleAnalyze = async () => {
    setError(null);
    setResult(null);

    if (!code.trim()) {
      setError("Please paste some Solidity code first.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed with ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-4xl space-y-6">
        <h1 className="text-3xl font-semibold">
          ThirdEye Solidity Auditor
        </h1>

        <p className="text-sm text-slate-300">
          Paste a Solidity contract and click Analyze to get a summary from the backend.
        </p>

        <textarea
          className="w-full h-64 rounded-md bg-slate-900 border border-slate-700 p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="Paste Solidity code here..."
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />

        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="px-4 py-2 rounded-md bg-emerald-500 text-slate-950 font-medium disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>

        {error && (
          <div className="text-sm text-red-400">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-4 space-y-4">
            <div>
              <h2 className="text-xl font-semibold">Summary</h2>
              <p className="text-sm text-slate-200 mt-1">
                {result.summary}
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold">Final Verdict</h2>
              <p className="text-sm text-slate-200 mt-1">
                {result.final_verdict ?? "N/A"}
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold">From Cache?</h2>
              <p className="text-sm text-slate-200 mt-1">
                {String(result.from_cache ?? false)}
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
