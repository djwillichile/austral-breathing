import { BiomeCoverageChart } from "@/components/charts/BiomeCoverageChart";
import { EnvironmentalSpaceChart } from "@/components/charts/EnvironmentalSpaceChart";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { VariabilityChart } from "@/components/charts/VariabilityChart";
import { useStations } from "@/lib/useStationData";

function GeographicReach() {
  const { data } = useStations();
  const perStation = data?.representativeness.perStation ?? [];
  return (
    <article className="atlas-card">
      <p className="section-eyebrow">Representativeness · geographic scope</p>
      <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
        How far each station stands in for its surroundings
      </h3>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line-soft)] text-left text-[11px] uppercase tracking-[0.2em] text-[var(--ink-muted)]">
              <th className="py-2 pr-4">Station</th>
              <th className="py-2 pr-4">Biome</th>
              <th className="py-2 pr-4">Nearest station</th>
              <th className="py-2 pr-4">Distance (km)</th>
              <th className="py-2">Indicative reach (km)</th>
            </tr>
          </thead>
          <tbody>
            {perStation.map((p) => (
              <tr key={p.siteId} className="border-b border-[var(--line-soft)] text-[var(--ink-soft)]">
                <td className="py-2 pr-4 font-semibold text-[var(--ink-strong)]">{p.siteId}</td>
                <td className="py-2 pr-4">{p.biome}</td>
                <td className="py-2 pr-4">{p.nearestNeighborId ?? "—"}</td>
                <td className="py-2 pr-4">{p.nearestNeighborKm ?? "—"}</td>
                <td className="py-2">{p.reachRadiusKm ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs leading-6 text-[var(--ink-muted)]">
        Indicative reach is half the distance to the nearest station — a simple proxy for the geographic extent a
        station represents in the absence of external climate surfaces. Larger reach means sparser regional coverage.
      </p>
    </article>
  );
}

export function AnalysisSection() {
  return (
    <section id="analysis" className="atlas-section border-y border-[var(--line-soft)] bg-[var(--paper-muted)]">
      <div className="container space-y-12">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-end">
          <div>
            <p className="section-eyebrow">Interactive analysis</p>
            <h2 className="font-[var(--font-display)] text-4xl leading-[0.95] text-[var(--ink-strong)] sm:text-5xl">
              Variables, variability, and how representative each station is.
            </h2>
          </div>
          <p className="max-w-3xl text-base leading-8 text-[var(--ink-soft)] sm:text-lg">
            Explore the standardized daily fluxes and meteorology, compare distributions across stations, and read each
            station's ecological and geographic representativeness — which ecosystem it samples and how much surrounding
            territory it stands in for.
          </p>
        </div>

        <TimeSeriesChart />
        <VariabilityChart />

        <div className="grid gap-8 xl:grid-cols-2">
          <EnvironmentalSpaceChart />
          <BiomeCoverageChart />
        </div>

        <GeographicReach />
      </div>
    </section>
  );
}
