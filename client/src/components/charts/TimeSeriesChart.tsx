import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  VARIABLE_META,
  useStations,
  useTimeseries,
} from "@/lib/useStationData";

const VARS = Object.keys(VARIABLE_META);

export function TimeSeriesChart() {
  const { data: stationsData } = useStations();
  const stations = stationsData?.stations ?? [];
  const [siteId, setSiteId] = useState<string | null>(null);
  const [variable, setVariable] = useState<string>("NEE");

  const activeSite = siteId ?? stations[0]?.siteId ?? null;
  const { data: ts, loading, error } = useTimeseries(activeSite);

  const series = useMemo(() => {
    if (!ts) return [];
    return ts.daily
      .filter((row) => row[variable] !== null && row[variable] !== undefined)
      .map((row) => ({ t: row.t as string, value: row[variable] as number }));
  }, [ts, variable]);

  const meta = VARIABLE_META[variable];

  return (
    <article className="atlas-card">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="section-eyebrow">Variable time series</p>
          <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
            Daily {meta?.label.toLowerCase()} <span className="text-[var(--ink-muted)]">({meta?.unit})</span>
          </h3>
        </div>
        <div className="flex flex-wrap gap-3">
          <select
            aria-label="Station"
            className="rounded-full border border-[var(--line-soft)] bg-[var(--paper)] px-4 py-2 text-sm"
            value={activeSite ?? ""}
            onChange={(e) => setSiteId(e.target.value)}
          >
            {stations.map((s) => (
              <option key={s.siteId} value={s.siteId}>
                {s.siteId} — {s.siteName}
              </option>
            ))}
          </select>
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
      </div>

      <div className="mt-6 h-[360px] w-full">
        {loading && <p className="text-sm text-[var(--ink-muted)]">Loading time series…</p>}
        {error && <p className="text-sm text-[var(--ink-muted)]">No time series available for this station.</p>}
        {!loading && !error && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0000000f" />
              <XAxis dataKey="t" tick={{ fontSize: 11 }} minTickGap={48} />
              <YAxis tick={{ fontSize: 11 }} width={52} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 12 }}
                formatter={(value: number) => [`${value} ${meta?.unit}`, variable]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={meta?.color}
                dot={false}
                strokeWidth={1.4}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
      <p className="mt-3 text-xs leading-6 text-[var(--ink-muted)]">
        {series.length.toLocaleString()} valid daily observations shown. Gaps are missing or QC-rejected days.
      </p>
    </article>
  );
}
