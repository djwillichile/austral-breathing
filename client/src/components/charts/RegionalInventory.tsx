import { useMemo, useState } from "react";
import {
  TIER_META,
  useRegionalInventory,
  type FluxTowerRecord,
} from "@/lib/useStationData";

function TierBadge({ tier }: { tier: number | null }) {
  const meta = tier ? TIER_META[tier] : null;
  if (!meta) return <span className="text-[var(--ink-muted)]">—</span>;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em]"
      style={{ borderColor: `${meta.color}40`, color: meta.color, backgroundColor: `${meta.color}12` }}
    >
      {meta.label}
    </span>
  );
}

/**
 * Regional inventory of the South American carbon-observation network: the
 * eddy-covariance CO₂ flux towers (by availability tier) and the complementary
 * carbon-stock programs, plus the documented country gaps. Fed by
 * regional_inventory.json (scripts_build_registry_web_data.py).
 */
export function RegionalInventory() {
  const { data, loading, error } = useRegionalInventory();
  const [tab, setTab] = useState<"flux" | "stock">("flux");

  const towersByCountry = useMemo(() => {
    if (!data) return [];
    const co2 = data.fluxTowers.filter((t) => t.measuresCo2 === "yes");
    const groups = new Map<string, FluxTowerRecord[]>();
    co2.forEach((t) => {
      const arr = groups.get(t.country) ?? [];
      arr.push(t);
      groups.set(t.country, arr);
    });
    return Array.from(groups.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [data]);

  if (loading) {
    return (
      <article className="atlas-card">
        <p className="section-eyebrow">Regional inventory · South America</p>
        <p className="mt-4 text-sm text-[var(--ink-muted)]">Loading inventory…</p>
      </article>
    );
  }

  if (error || !data) {
    return (
      <article className="atlas-card">
        <p className="section-eyebrow">Regional inventory · South America</p>
        <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
          The carbon-observation network across South America
        </h3>
        <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
          The inventory layer has not been generated for this build. Produce it with:
        </p>
        <pre className="mt-4 overflow-x-auto rounded-xl bg-[var(--paper-strong)] p-4 text-xs leading-6 text-[var(--ink-strong)]">
{`python scripts_build_registry_web_data.py`}
        </pre>
      </article>
    );
  }

  const s = data.summary;

  return (
    <article className="atlas-card">
      <p className="section-eyebrow">Regional inventory · South America</p>
      <h3 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">
        The carbon-observation network across South America
      </h3>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--ink-soft)]">
        Two complementary systems: eddy-covariance towers that measure CO₂ <em>fluxes</em> (NEE → GPP/Reco) and
        plot/inventory programs that measure carbon <em>stock</em> (biomass, peat, soil). Records carry an
        availability tier and a confidence level; see each source for verification.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="metric-box"><span>CO₂ flux towers</span><strong>{s.fluxTowersCo2}</strong></div>
        <div className="metric-box"><span>Open / archived</span><strong>{s.fluxTowersOpen}</strong></div>
        <div className="metric-box"><span>Stock programs</span><strong>{s.stockPrograms}</strong></div>
        <div className="metric-box"><span>Countries w/ towers</span><strong>{Object.keys(s.byCountry).length}</strong></div>
      </div>

      <div className="mt-6 inline-flex gap-1 rounded-lg bg-[var(--paper-strong)] p-1">
        <button
          onClick={() => setTab("flux")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium ${tab === "flux" ? "bg-[var(--paper)] text-[var(--ink-strong)]" : "text-[var(--ink-soft)]"}`}
        >
          Flux towers (CO₂)
        </button>
        <button
          onClick={() => setTab("stock")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium ${tab === "stock" ? "bg-[var(--paper)] text-[var(--ink-strong)]" : "text-[var(--ink-soft)]"}`}
        >
          Stock programs
        </button>
      </div>

      {tab === "flux" ? (
        <div className="mt-6 space-y-8">
          {towersByCountry.map(([country, towers]) => (
            <div key={country}>
              <h4 className="font-[var(--font-display)] text-lg text-[var(--ink-strong)]">
                {country} <span className="text-[var(--ink-muted)]">· {towers.length}</span>
              </h4>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--line-soft)] text-left text-[11px] uppercase tracking-[0.18em] text-[var(--ink-muted)]">
                      <th className="py-2 pr-3">Site</th>
                      <th className="py-2 pr-3">Ecosystem</th>
                      <th className="py-2 pr-3">Network</th>
                      <th className="py-2 pr-3">Availability</th>
                      <th className="py-2">Access</th>
                    </tr>
                  </thead>
                  <tbody>
                    {towers.map((t) => (
                      <tr key={t.siteId} className="border-b border-[var(--line-soft)] text-[var(--ink-soft)]">
                        <td className="py-2 pr-3">
                          <a href={t.sourceUrl} target="_blank" rel="noreferrer" className="font-semibold text-[var(--ink-strong)] underline-offset-2 hover:underline">
                            {t.siteId}
                          </a>
                          <div className="text-xs text-[var(--ink-muted)]">{t.siteName}</div>
                        </td>
                        <td className="py-2 pr-3">{t.biome}</td>
                        <td className="py-2 pr-3">{t.network}</td>
                        <td className="py-2 pr-3"><TierBadge tier={t.tier} /></td>
                        <td className="py-2 text-xs">{t.dataAccess}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          <p className="text-xs leading-6 text-[var(--ink-muted)]">
            Documented country gaps (no confirmed open/published CO₂ tower): {data.fluxGapCountries.join(", ")}.
            Uruguay has only an energy/ET tower; Venezuela only historic/ambiguous measurements.
          </p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--line-soft)] text-left text-[11px] uppercase tracking-[0.18em] text-[var(--ink-muted)]">
                <th className="py-2 pr-3">Program</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Coverage</th>
                <th className="py-2 pr-3">Availability</th>
                <th className="py-2">Access</th>
              </tr>
            </thead>
            <tbody>
              {data.stockPrograms.map((p) => (
                <tr key={p.program} className="border-b border-[var(--line-soft)] text-[var(--ink-soft)]">
                  <td className="py-2 pr-3">
                    <a href={p.sourceUrl} target="_blank" rel="noreferrer" className="font-semibold text-[var(--ink-strong)] underline-offset-2 hover:underline">
                      {p.program}
                    </a>
                  </td>
                  <td className="py-2 pr-3">{p.stockType}</td>
                  <td className="py-2 pr-3 text-xs">{p.countries}</td>
                  <td className="py-2 pr-3"><TierBadge tier={p.tier} /></td>
                  <td className="py-2 text-xs">{p.dataAccess}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}
