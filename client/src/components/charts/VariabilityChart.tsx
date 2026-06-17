import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { VARIABLE_META, useStations, useStats } from "@/lib/useStationData";

const VARS = Object.keys(VARIABLE_META);

export function VariabilityChart() {
  const { data: stats, loading } = useStats();
  const { data: stationsData } = useStations();
  const [variable, setVariable] = useState<string>("NEE");

  const colorBySite = useMemo(() => {
    const map: Record<string, string> = {};
    (stationsData?.stations ?? []).forEach((s) => (map[s.siteId] = s.qualityColor));
    return map;
  }, [stationsData]);

  const rows = useMemo(() => {
    if (!stats) return [];
    return stats.perStation
      .map((st) => {
        const v = st.variables[variable];
        if (!v || v.mean === null) return null;
        return {
          siteId: st.siteId,
          mean: v.mean,
          // Asymmetric error bar from the p5–p95 spread (variability).
          errLow: v.mean - (v.p5 ?? v.mean),
          errHigh: (v.p95 ?? v.mean) - v.mean,
          sd: v.sd,
          n: v.n,
        };
      })
      .filter(Boolean) as {
      siteId: string;
      mean: number;
      errLow: number;
      errHigh: number;
      sd: number | null;
      n: number | null;
    }[];
  }, [stats, variable]);

  const meta = VARIABLE_META[variable];

  return (
    <article className="atlas-card">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="section-eyebrow">Statistics & variability</p>
          <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
            {meta?.label} across stations <span className="text-[var(--ink-muted)]">({meta?.unit})</span>
          </h3>
        </div>
        <select
          aria-label="Variable"
          className="rounded-full border border-[var(--line-soft)] bg-[var(--paper)] px-4 py-2 text-sm"
          value={variable}
          onChange={(e) => setVariable(e.target.value)}
        >
          {VARS.map((v) => (
            <option key={v} value={v}>
              {v} — {VARIABLE_META[v].label}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-6 h-[340px] w-full">
        {loading ? (
          <p className="text-sm text-[var(--ink-muted)]">Loading statistics…</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0000000f" />
              <XAxis dataKey="siteId" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={52} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 12 }}
                formatter={(value: number, name: string) =>
                  name === "mean" ? [`${value} ${meta?.unit}`, "Mean"] : [value, name]
                }
              />
              <Bar dataKey="mean" radius={[6, 6, 0, 0]} isAnimationActive={false}>
                {rows.map((r) => (
                  <Cell key={r.siteId} fill={colorBySite[r.siteId] ?? meta?.color} />
                ))}
                <ErrorBar dataKey="errHigh" width={4} strokeWidth={1.2} stroke="#33333399" direction="y" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      <p className="mt-3 text-xs leading-6 text-[var(--ink-muted)]">
        Bars show the per-station mean; whiskers mark the p5–p95 daily spread, a compact view of each station's
        variability. Bar color follows the project utility class.
      </p>
    </article>
  );
}
