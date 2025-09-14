"use client";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

type Attempt = { created_at: string; percentage: number | null };

export default function MarksChart() {
  const [attempts, setAttempts] = useState<Attempt[]>([]);

  useEffect(() => {
    async function load() {
      // Get first subject
      const us = await supabase.from("user_subjects").select("subject_id");
      const sid = us.data?.[0]?.subject_id || null;
      if (!sid) { setAttempts([]); return; }
      const pa = await supabase
        .from("paper_attempts")
        .select("created_at, percentage")
        .eq("subject_id", sid)
        .order("created_at", { ascending: true })
        .limit(200);
      setAttempts(pa.data || []);
    }
    load();
  }, []);

  const data = (attempts || []).filter(a => typeof a.percentage === "number").map((a, i) => ({
    i,
    date: new Date(a.created_at).toLocaleDateString(),
    pct: Number(a.percentage),
  }));

  // Simple linear trend (least squares)
  const trend = (() => {
    const N = data.length;
    if (N < 2) return null;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    data.forEach(d => { sumX += d.i; sumY += d.pct; sumXY += d.i * d.pct; sumXX += d.i * d.i });
    const m = (N * sumXY - sumX * sumY) / (N * sumXX - sumX * sumX || 1);
    const b = (sumY - m * sumX) / N;
    const nextX = N;
    const nextY = Math.max(0, Math.min(100, m * nextX + b));
    return { m, b, nextY };
  })();

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="mb-2 text-sm text-white/70">Performance Over Time</div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: 12, right: 12, top: 8, bottom: 8 }}>
            <XAxis dataKey="date" hide />
            <YAxis domain={[0, 100]} tick={{ fill: "#ddd", fontSize: 12 }} />
            <Tooltip
              contentStyle={{ background: "#111", border: "1px solid rgba(255,255,255,.1)" }}
              labelStyle={{ color: "#fff" }}
              formatter={(v: number) => [`${v}%`, "Score"]}
            />
            <Line type="monotone" dataKey="pct" stroke="#ffffff" strokeWidth={2} dot={false} />
            {trend && (
              <>
                {/* Next predicted marker */}
                <ReferenceLine y={trend.nextY} stroke="rgba(255,255,255,.4)" strokeDasharray="4 4" />
              </>
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {trend && (
        <div className="mt-2 text-sm text-white/80">
          If you continue at this pace, your next score may be around {" "}
          <span className="font-semibold">{Math.round(trend.nextY)}%</span>.
        </div>
      )}
    </div>
  );
}
