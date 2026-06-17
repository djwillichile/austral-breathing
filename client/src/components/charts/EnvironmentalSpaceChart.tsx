import { useMemo } from "react";
import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { biomeColor, useStations, useStats } from "@/lib/useStationData";

/**
 * Environmental-space coverage: each station positioned by its mean air
 * temperature and mean incoming shortwave, coloured by biome. Shows how much
 * of the measured environmental space the network spans and whether biomes
 * cluster or are isolated.
 */
export function EnvironmentalSpaceChart() {
  const { data: stats, loading } = useStats();
  const { data: stationsData } = useStations();

  const points = useMemo(() => {
    if (!stats || !stationsData) return [];
    const biomeBySite: Record<string, string> = {};
    const obsBySite: Record<string, number> = {};
    stationsData.stations.forEach((s) => {
      biomeBySite[s.siteId] = s.ecosystemBiome || "Unknown";
      obsBySite[s.siteId] = s.observations;
    });
    return stats.perStation
      .map((st) => {
        const ta = st.variables.TA?.mean;
        const sw = st.variables.SW_IN?.mean;
        if (ta === null || ta === undefined || sw === null || sw === undefined) return null;
        return {
          siteId: st.siteId,
          ta,
          sw,
          biome: biomeBySite[st.siteId] ?? "Unknown",
          obs: obsBySite[st.siteId] ?? 0,
        };
      })
      .filter(Boolean) as { siteId: string; ta: number; sw: number; biome: string; obs: number }[];
  }, [stats, stationsData]);

  const biomes = Array.from(new Set(points.map((p) => p.biome)));

  return (
    <article className="atlas-card">
      <p className="section-eyebrow">Representativeness · environmental space</p>
      <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
        Which part of the climate envelope each station samples
      </h3>

      <div className="mt-6 h-[360px] w-full">
        {loading ? (
          <p className="text-sm text-[var(--ink-muted)]">Loading environmental space…</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 24, bottom: 28, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0000000f" />
              <XAxis
                type="number"
                dataKey="ta"
                name="Mean air temperature"
                unit=" °C"
                tick={{ fontSize: 11 }}
                label={{ value: "Mean air temperature (°C)", position: "bottom", fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="sw"
                name="Mean incoming shortwave"
                unit=" W/m²"
                tick={{ fontSize: 11 }}
                width={64}
                label={{ value: "Mean SW_IN (W/m²)", angle: -90, position: "insideLeft", fontSize: 11 }}
              />
              <ZAxis type="number" dataKey="obs" range={[80, 420]} name="Observations" />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{ fontSize: 12, borderRadius: 12 }}
                formatter={(value: number, name: string) => [value, name]}
                labelFormatter={() => ""}
                content={({ payload }) => {
                  const p = payload?.[0]?.payload as
                    | { siteId: string; ta: number; sw: number; biome: string }
                    | undefined;
                  if (!p) return null;
                  return (
                    <div className="rounded-xl border border-[var(--line-soft)] bg-white p-3 text-xs">
                      <strong>{p.siteId}</strong> · {p.biome}
                      <br />
                      TA {p.ta} °C · SW_IN {p.sw} W/m²
                    </div>
                  );
                }}
              />
              <Scatter data={points} isAnimationActive={false}>
                {points.map((p) => (
                  <Cell key={p.siteId} fill={biomeColor(p.biome)} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        {biomes.map((b) => (
          <span key={b} className="inline-flex items-center gap-2 text-xs text-[var(--ink-soft)]">
            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: biomeColor(b) }} />
            {b}
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs leading-6 text-[var(--ink-muted)]">
        Marker size scales with the number of observations. Stations that sit alone in this space sample conditions
        no other station represents.
      </p>
    </article>
  );
}
