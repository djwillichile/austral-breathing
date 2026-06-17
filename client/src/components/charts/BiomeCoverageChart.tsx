import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { biomeColor, useStations } from "@/lib/useStationData";

/**
 * Biome representativeness: how many stations stand for each ecosystem of the
 * Southern Cone, and which stations are the sole representative of their biome.
 */
export function BiomeCoverageChart() {
  const { data, loading } = useStations();
  const coverage = data?.representativeness.biomeCoverage ?? [];
  const perStation = data?.representativeness.perStation ?? [];
  const soleReps = perStation.filter((p) => p.soleRepresentative);

  return (
    <article className="atlas-card">
      <p className="section-eyebrow">Representativeness · biome coverage</p>
      <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
        Ecosystems represented across the inventory
      </h3>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="h-[300px] w-full">
          {loading ? (
            <p className="text-sm text-[var(--ink-muted)]">Loading biome coverage…</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={coverage}
                margin={{ top: 8, right: 32, bottom: 8, left: 8 }}
              >
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="biome" width={150} tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 12 }} />
                <Bar dataKey="stationCount" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                  {coverage.map((c) => (
                    <Cell key={c.biome} fill={biomeColor(c.biome)} />
                  ))}
                  <LabelList dataKey="stationCount" position="right" fontSize={11} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="space-y-3 text-sm leading-7 text-[var(--ink-soft)]">
          <p className="font-semibold text-[var(--ink-strong)]">Sole representatives</p>
          <p className="text-xs text-[var(--ink-muted)]">
            Stations that are the only one sampling their biome — losing them leaves that ecosystem unmonitored.
          </p>
          <div className="flex flex-wrap gap-2">
            {soleReps.map((p) => (
              <span
                key={p.siteId}
                className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs"
                style={{ backgroundColor: `${biomeColor(p.biome)}1a`, color: biomeColor(p.biome) }}
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: biomeColor(p.biome) }} />
                {p.siteId} · {p.biome}
              </span>
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}
