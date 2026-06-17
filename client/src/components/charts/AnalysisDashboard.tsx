import { Activity, BarChart3, Compass, Map as MapIcon } from "lucide-react";
import { BiomeCoverageChart } from "@/components/charts/BiomeCoverageChart";
import { ClimateRepresentativeness } from "@/components/charts/ClimateRepresentativeness";
import { EnvironmentalSpaceChart } from "@/components/charts/EnvironmentalSpaceChart";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { VariabilityChart } from "@/components/charts/VariabilityChart";
import { LeafletMap } from "@/components/LeafletMap";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
        Indicative reach is half the distance to the nearest station — a simple geographic proxy. The climate-space
        surface above is the rigorous counterpart, weighing actual environmental similarity rather than distance alone.
      </p>
    </article>
  );
}

const TABS = [
  { value: "timeseries", label: "Time series", icon: Activity },
  { value: "statistics", label: "Statistics", icon: BarChart3 },
  { value: "map", label: "Map", icon: MapIcon },
  { value: "representativeness", label: "Representativeness", icon: Compass },
];

/**
 * Tabbed analysis dashboard. Groups the interactive views into four panes so
 * the section reads as one workbench rather than a long scroll: daily series,
 * distribution statistics, the regional map, and ecological + climate-space
 * representativeness.
 */
export function AnalysisDashboard() {
  return (
    <Tabs defaultValue="timeseries" className="w-full gap-6">
      <TabsList className="h-auto flex-wrap gap-1 bg-[var(--paper-strong)] p-1">
        {TABS.map(({ value, label, icon: Icon }) => (
          <TabsTrigger
            key={value}
            value={value}
            className="data-[state=active]:bg-[var(--paper)] data-[state=active]:text-[var(--ink-strong)] gap-2 px-4 py-2 text-[var(--ink-soft)]"
          >
            <Icon className="h-4 w-4" />
            {label}
          </TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="timeseries" className="space-y-8">
        <TimeSeriesChart />
      </TabsContent>

      <TabsContent value="statistics" className="space-y-8">
        <VariabilityChart />
      </TabsContent>

      <TabsContent value="map" className="space-y-8">
        <article className="atlas-card overflow-hidden p-3 sm:p-4">
          <LeafletMap className="atlas-map h-[620px] rounded-[28px]" />
        </article>
      </TabsContent>

      <TabsContent value="representativeness" className="space-y-8">
        <ClimateRepresentativeness />
        <div className="grid gap-8 xl:grid-cols-2">
          <EnvironmentalSpaceChart />
          <BiomeCoverageChart />
        </div>
        <GeographicReach />
      </TabsContent>
    </Tabs>
  );
}
