import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useRef } from "react";
import { stationData } from "@/lib/stationsData";
import {
  representativenessColor,
  useRepresentativenessGrid,
  type RepresentativenessGrid,
} from "@/lib/useStationData";

function formatKm2(value: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

/** Paints the representativeness surface as a coloured cell grid on Leaflet. */
function RepresentativenessSurface({ data }: { data: RepresentativenessGrid }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const { grid, bbox } = data;

    const map = L.map(container.current, { zoomControl: true, attributionControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 12,
      opacity: 0.55,
    }).addTo(map);

    // One translucent rectangle per (downsampled) climate cell.
    for (let row = 0; row < grid.nLat; row++) {
      for (let col = 0; col < grid.nLon; col++) {
        const score = grid.rep[row * grid.nLon + col];
        if (score === null || score === undefined) continue;
        const lat = grid.latStart + row * grid.dLat;
        const lon = grid.lonStart + col * grid.dLon;
        L.rectangle(
          [
            [lat, lon],
            [lat + grid.dLat, lon + grid.dLon],
          ],
          {
            stroke: false,
            fillColor: representativenessColor(score),
            fillOpacity: 0.6,
            interactive: false,
          }
        ).addTo(map);
      }
    }

    // Station markers on top of the surface.
    stationData.forEach((s) => {
      L.circleMarker([s.lat, s.lon], {
        radius: 5,
        color: "#ffffff",
        weight: 2,
        fillColor: "#1c2a20",
        fillOpacity: 1,
      })
        .bindTooltip(`${s.siteId} · ${s.siteName}`, { direction: "top" })
        .addTo(map);
    });

    map.fitBounds([
      [bbox.lat_min, bbox.lon_min],
      [bbox.lat_max, bbox.lon_max],
    ]);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [data]);

  return <div ref={container} className="atlas-map h-[560px] w-full rounded-[24px]" />;
}

function LegendRamp() {
  const stops = [0, 0.25, 0.5, 0.75, 1];
  return (
    <div className="flex items-center gap-3 text-xs text-[var(--ink-soft)]">
      <span>Environmental gap</span>
      <span className="flex h-3 w-40 overflow-hidden rounded-full">
        {stops.slice(0, -1).map((s, i) => (
          <span
            key={s}
            className="flex-1"
            style={{
              background: `linear-gradient(to right, ${representativenessColor(s)}, ${representativenessColor(
                stops[i + 1]
              )})`,
            }}
          />
        ))}
      </span>
      <span>Well represented</span>
    </div>
  );
}

/**
 * Rigorous environmental representativeness: a climate-space view of how much
 * of the Southern Cone the station network stands in for. Renders only once
 * `representativeness_grid.json` has been produced by
 * `scripts_representativeness_analysis.py`; otherwise it explains how to build it.
 */
export function ClimateRepresentativeness() {
  const { data, loading, error } = useRepresentativenessGrid();

  if (loading) {
    return (
      <article className="atlas-card">
        <p className="section-eyebrow">Representativeness · climate space</p>
        <p className="mt-4 text-sm text-[var(--ink-muted)]">Loading representativeness surface…</p>
      </article>
    );
  }

  if (error || !data) {
    return (
      <article className="atlas-card">
        <p className="section-eyebrow">Representativeness · climate space</p>
        <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
          A regional climate-space representativeness surface
        </h3>
        <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
          This view maps how well the network represents the Southern Cone in multivariate climate space, using
          WorldClim bioclimatic surfaces. The analysis layer has not been generated for this build. Produce it with:
        </p>
        <pre className="mt-4 overflow-x-auto rounded-xl bg-[var(--paper-strong)] p-4 text-xs leading-6 text-[var(--ink-strong)]">
{`# real climate (needs outbound access to the WorldClim mirror)
python scripts_representativeness_analysis.py --download

# or a synthetic, clearly-labelled demonstration surface
python scripts_representativeness_analysis.py --demo`}
        </pre>
      </article>
    );
  }

  return (
    <article className="atlas-card">
      <p className="section-eyebrow">Representativeness · climate space</p>
      <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
        How much of the Southern Cone the network represents in climate space
      </h3>

      {data.synthetic && (
        <p className="mt-4 rounded-xl border border-[var(--accent-copper)]/40 bg-[var(--accent-copper)]/10 px-4 py-3 text-xs leading-6 text-[var(--ink-strong)]">
          <strong>Synthetic demonstration surface.</strong> This build uses an analytic mock-up climate field, not
          measured data — run the analysis with real WorldClim rasters (<code>--download</code>) to replace it.
        </p>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div>
          <RepresentativenessSurface data={data} />
          <div className="mt-4">
            <LegendRamp />
          </div>
        </div>

        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <div className="metric-box">
              <span>Region represented</span>
              <strong>{(data.coverageFraction * 100).toFixed(0)}%</strong>
            </div>
            <div className="metric-box">
              <span>Within</span>
              <strong>{data.thresholdSd} SD</strong>
            </div>
          </div>
          <p className="text-xs leading-6 text-[var(--ink-muted)]">
            Share of the regional area lying within {data.thresholdSd} standard deviation of a station in the
            standardised climate space spanned by {data.variables.map((v) => v.label).join(", ")}.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--line-soft)] text-left text-[11px] uppercase tracking-[0.2em] text-[var(--ink-muted)]">
                  <th className="py-2 pr-3">Station</th>
                  <th className="py-2 pr-3">Represents</th>
                  <th className="py-2">Median dissim.</th>
                </tr>
              </thead>
              <tbody>
                {data.perStation.map((p) => (
                  <tr key={p.siteId} className="border-b border-[var(--line-soft)] text-[var(--ink-soft)]">
                    <td className="py-2 pr-3 font-semibold text-[var(--ink-strong)]">{p.siteId}</td>
                    <td className="py-2 pr-3">
                      {p.representativeAreaPct.toFixed(1)}%
                      <span className="text-[var(--ink-muted)]"> · {formatKm2(p.representativeAreaKm2)} km²</span>
                    </td>
                    <td className="py-2">{p.medianDissimilarity.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <p className="mt-5 text-xs leading-6 text-[var(--ink-muted)]">
        {data.method} Source: {data.source}. Each station's representative area is the territory for which it is the
        closest environmental analogue within the similarity threshold.
      </p>
    </article>
  );
}
