// Design reminder: regional scientific editorialism with cartographic modernism.
// Every section should feel like a field atlas plate: asymmetrical, traceable, calm, and publication-oriented.

import { AnalysisSection } from "@/components/charts/AnalysisSection";
import { LeafletMap } from "@/components/LeafletMap";
import { projectStats, stationData, type StationRecord } from "@/lib/stationsData";
import {
  ArrowRight,
  ExternalLink,
  Leaf,
  MapPinned,
  Microscope,
  NotebookText,
  Trees,
  Waves,
} from "lucide-react";

const heroImage =
  "https://d2xsxph8kpxj0f.cloudfront.net/310519663087934505/Uo4BULSidzNW4LZtgw5kEu/patagonia_atlas_hero_reference-44rCShK7gWHnhZNc6mKtna.webp";
const forestImage =
  "https://d2xsxph8kpxj0f.cloudfront.net/310519663087934505/Uo4BULSidzNW4LZtgw5kEu/patagonia_station_forest_panel-FRm5oNWTz7DYHhLgbGbERf.webp";
const peatlandImage =
  "https://d2xsxph8kpxj0f.cloudfront.net/310519663087934505/Uo4BULSidzNW4LZtgw5kEu/patagonia_peatland_plate-W6TU88NQPXwKbnZ6Xze5q6.webp";
const methodsImage =
  "https://d2xsxph8kpxj0f.cloudfront.net/310519663087934505/Uo4BULSidzNW4LZtgw5kEu/patagonia_methods_collage-LQnaSUDEBb5JQLaDmxcdvB.webp";

const navigation = [
  { label: "Overview", href: "#overview" },
  { label: "Stations", href: "#stations" },
  { label: "Map", href: "#map" },
  { label: "Analysis", href: "#analysis" },
  { label: "Methods", href: "#methods" },
  { label: "Results", href: "#results" },
  { label: "About", href: "#about" },
];

const workflow = [
  {
    title: "Discovery and validation",
    text: "The workflow begins from officially distributed station products and a programmatic inventory generated through FLUXNET Shuttle, preserving traceability from network source to local archive.",
  },
  {
    title: "Raw archive preservation",
    text: "Original FLUXNET ZIP packages remain untouched in the raw data layer so that downstream products never replace the primary files obtained from the official distribution channel.",
  },
  {
    title: "Variable standardization",
    text: "Daily products are harmonized to a common set of flux and meteorological variables, with missing sentinels converted to null values and quality-control columns retained whenever present.",
  },
  {
    title: "Comparative scoring",
    text: "Each station receives a compact utility score derived from temporal coverage, completeness, and acceptable QC share, allowing regional comparison without obscuring site-level detail.",
  },
];

const deliverables = [
  "Structured station metadata and download traceability tables",
  "Processed daily standardized files for each validated site",
  "Comparative quality and variable-availability summaries",
  "An interactive browser map for public-facing exploration",
];

const methodsFigures = [
  {
    title: "Forest station context",
    image: forestImage,
    text: "A field-atlas framing of the temperate rainforest tower environment, used to visually anchor the Chilean station narrative.",
  },
  {
    title: "Peatland station context",
    image: peatlandImage,
    text: "A companion visual plate for wetland flux sites, emphasizing the peatland landscape surrounding CL-SDP and southern comparator bogs.",
  },
];

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function SectionHeader({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-end">
      <div>
        <p className="section-eyebrow">{eyebrow}</p>
        <h2 className="font-[var(--font-display)] text-4xl leading-[0.95] text-[var(--ink-strong)] sm:text-5xl">
          {title}
        </h2>
      </div>
      <p className="max-w-3xl text-base leading-8 text-[var(--ink-soft)] sm:text-lg">{body}</p>
    </div>
  );
}

function MetricPlate({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <article className="atlas-card atlas-card-dense">
      <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--ink-muted)]">
        {label}
      </p>
      <p className="mt-4 font-[var(--font-display)] text-4xl leading-none text-[var(--ink-strong)] sm:text-5xl">
        {value}
      </p>
      <p className="mt-4 text-sm leading-6 text-[var(--ink-soft)]">{note}</p>
    </article>
  );
}

function QualityBadge({ qualityClass, color }: { qualityClass: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em]"
      style={{
        borderColor: `${color}40`,
        color,
        backgroundColor: `${color}14`,
      }}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      {qualityClass} utility
    </span>
  );
}

function StationCard({ station }: { station: StationRecord }) {
  return (
    <article className="atlas-card group h-full overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-[var(--line-soft)] pb-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.34em] text-[var(--ink-muted)]">
            {station.siteId}
          </p>
          <h3 className="mt-3 font-[var(--font-display)] text-3xl leading-[1.02] text-[var(--ink-strong)]">
            {station.siteName}
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-7 text-[var(--ink-soft)]">{station.ecosystem}</p>
        </div>
        <QualityBadge qualityClass={station.qualityClass} color={station.qualityColor} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="space-y-3 text-sm leading-7 text-[var(--ink-soft)]">
          <p>
            <span className="font-semibold text-[var(--ink-strong)]">Country:</span> {station.country}
          </p>
          <p>
            <span className="font-semibold text-[var(--ink-strong)]">Regional scope:</span> {station.regionalScope}
          </p>
          <p>
            <span className="font-semibold text-[var(--ink-strong)]">Coverage:</span> {station.yearStart}–{station.yearEnd}
          </p>
          <p>
            <span className="font-semibold text-[var(--ink-strong)]">Observations:</span> {formatNumber(station.observations)} daily rows
          </p>
          <p>
            <span className="font-semibold text-[var(--ink-strong)]">Product DOI:</span> {station.productId}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="metric-box">
            <span>Utility score</span>
            <strong>{station.utilityScore.toFixed(3)}</strong>
          </div>
          <div className="metric-box">
            <span>Acceptable QC</span>
            <strong>{station.acceptableQcPct.toFixed(1)}%</strong>
          </div>
          <div className="metric-box">
            <span>Valid NEE</span>
            <strong>{station.validNeePct.toFixed(1)}%</strong>
          </div>
          <div className="metric-box">
            <span>Variables</span>
            <strong>{station.variablesAvailableCount}</strong>
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2 border-t border-[var(--line-soft)] pt-5">
        {station.variablesPresent.map((variable) => (
          <span key={`${station.siteId}-${variable}`} className="data-chip">
            {variable}
          </span>
        ))}
      </div>
    </article>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-[var(--paper)] text-[var(--ink-strong)]">
      <header className="sticky top-0 z-50 border-b border-[var(--line-soft)] bg-[rgba(248,244,235,0.84)] backdrop-blur-xl">
        <div className="container grid gap-5 py-4 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-center">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.34em] text-[var(--ink-muted)]">
              Eddy Covariance Atlas
            </p>
            <p className="mt-2 font-[var(--font-display)] text-2xl leading-none text-[var(--ink-strong)]">
              Chile & Patagonia
            </p>
          </div>
          <nav className="flex flex-wrap gap-x-6 gap-y-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--ink-muted)]">
            {navigation.map((item) => (
              <a key={item.href} href={item.href} className="transition-colors duration-300 hover:text-[var(--ink-strong)]">
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main>
        <section id="overview" className="atlas-section atlas-hero-section">
          <div className="container space-y-10 xl:space-y-12">
            <div className="grid gap-10 xl:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)] xl:items-start 2xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
              <div className="max-w-[31.5rem] xl:pt-8">
                <p className="section-eyebrow">Regional scientific atlas</p>
                <h1 className="max-w-[14.2ch] font-[var(--font-display)] text-[3.2rem] leading-[0.94] text-[var(--ink-strong)] sm:text-[3.75rem] xl:text-[4rem] 2xl:text-[4.35rem]">
                  A documented<br />
                  eddy covariance inventory<br />
                  for southern Chile<br />
                  and nearby Patagonia.
                </h1>
                <p className="mt-6 max-w-[34ch] text-[0.98rem] leading-[2rem] text-[var(--ink-soft)] xl:text-[1.02rem] xl:leading-[2.05rem]">
                  This project assembles validated stations, preserved FLUXNET archives, standardized daily variables,
                  comparative quality indicators, and a browser-ready interactive map built from a reproducible workflow
                  centered on programmatic access rather than manual collection.
                </p>

                <div className="mt-6 flex flex-wrap gap-4">
                  <button className="atlas-button atlas-button-primary" onClick={() => scrollToSection("stations")}>
                    Explore stations
                    <ArrowRight className="h-4 w-4" />
                  </button>
                  <button className="atlas-button atlas-button-secondary" onClick={() => scrollToSection("map")}>
                    View regional map
                    <MapPinned className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="space-y-6">
                <article className="hero-image-frame min-h-[29rem] xl:min-h-[32rem] 2xl:min-h-[34rem]">
                  <img
                    src={heroImage}
                    alt="Scientific atlas-style illustration of a temperate rainforest and peatland eddy covariance site in northern Patagonia"
                    className="h-full w-full scale-[1.08] object-cover object-[50%_28%]"
                  />
                </article>

                <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
                  <article className="atlas-card atlas-card-tall">
                    <p className="section-eyebrow">Project intent</p>
                    <p className="mt-4 text-lg leading-9 text-[var(--ink-soft)]">
                      The repository is structured as both an analytical workflow and an editorially legible archive. It is
                      designed for station discovery, download traceability, methodological review, and later publication as a
                      public-facing resource.
                    </p>
                    <div className="mt-8 grid gap-3">
                      {deliverables.map((item) => (
                        <div key={item} className="evidence-row">
                          <span className="evidence-dot" />
                          <p>{item}</p>
                        </div>
                      ))}
                    </div>
                  </article>

                  <article className="atlas-card atlas-card-tall bg-[var(--paper-strong)]">
                    <p className="section-eyebrow">Regional focus</p>
                    <div className="mt-6 grid gap-5 text-sm leading-7 text-[var(--ink-soft)]">
                      <div className="flex gap-4">
                        <Trees className="mt-1 h-5 w-5 text-[var(--accent-forest)]" />
                        <p>
                          Chilean sites emphasize temperate rainforest and peatland environments, with Chiloé as the current
                          narrative center of the atlas.
                        </p>
                      </div>
                      <div className="flex gap-4">
                        <Waves className="mt-1 h-5 w-5 text-[var(--accent-copper)]" />
                        <p>
                          Southern Argentine bog sites extend the comparison toward Tierra del Fuego, helping contextualize
                          Patagonia-scale wetland variability.
                        </p>
                      </div>
                      <div className="flex gap-4">
                        <Leaf className="mt-1 h-5 w-5 text-[var(--accent-forest)]" />
                        <p>
                          The present implementation privileges openly accessible products, but the workflow is designed to grow
                          toward additional official hubs as access conditions allow.
                        </p>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricPlate
                label="Validated stations"
                value={String(projectStats.stationCount)}
                note="Six programmatically obtained FLUXNET products currently anchor the regional inventory."
              />
              <MetricPlate
                label="Observation span"
                value={`${projectStats.yearMin}–${projectStats.yearMax}`}
                note="Daily standardized records extend from the earliest available southern Chilean stations to the newest comparator site."
              />
              <MetricPlate
                label="Total daily rows"
                value={formatNumber(projectStats.observationSum)}
                note="All observations shown here come from standardized daily products built from preserved raw archives."
              />
              <MetricPlate
                label="Highest utility site"
                value={projectStats.topSiteId}
                note="The current comparative scoring highlights the strongest combination of completeness, coverage, and QC acceptance."
              />
            </div>
          </div>
        </section>

        <section id="stations" className="atlas-section border-y border-[var(--line-soft)] bg-[var(--paper-muted)]">
          <div className="container space-y-12">
            <SectionHeader
              eyebrow="Stations"
              title="Validated sites organized as an analytical field inventory."
              body="Each station card combines official identity, ecological context, processed record span, observation count, and a comparative utility score so that the web interface remains as traceable as the underlying repository."
            />

            <div className="grid gap-6 xl:grid-cols-2">
              {stationData.map((station) => (
                <StationCard key={station.siteId} station={station} />
              ))}
            </div>
          </div>
        </section>

        <section id="map" className="atlas-section">
          <div className="container space-y-12">
            <SectionHeader
              eyebrow="Interactive map"
              title="A regional interface for spatial comparison across the current working inventory."
              body="Marker color represents the project utility class and marker size follows the number of standardized daily observations. Selecting a point reveals the same site evidence tracked in the summary tables."
            />

            <div className="grid gap-8 xl:grid-cols-[minmax(0,0.4fr)_minmax(0,1.6fr)]">
              <article className="atlas-card xl:sticky xl:top-28 xl:h-fit">
                <p className="section-eyebrow">Legend</p>
                <div className="mt-6 space-y-4 text-sm leading-7 text-[var(--ink-soft)]">
                  <div className="legend-row">
                    <span className="legend-swatch" style={{ backgroundColor: "#2F6B3B" }} />
                    <p>High utility, stronger completeness and QC acceptance.</p>
                  </div>
                  <div className="legend-row">
                    <span className="legend-swatch" style={{ backgroundColor: "#C78C1B" }} />
                    <p>Medium utility, useful coverage with more limited quality balance.</p>
                  </div>
                  <div className="legend-row">
                    <span className="legend-swatch" style={{ backgroundColor: "#9D3D2C" }} />
                    <p>Low utility, reserved for future expansions where coverage or QC may be substantially weaker.</p>
                  </div>
                </div>

                <div className="mt-8 border-t border-[var(--line-soft)] pt-6 text-sm leading-7 text-[var(--ink-soft)]">
                  <p>
                    The live web map complements the exported HTML map in the repository by giving the project a deployable,
                    frontend-only spatial interface suitable for GitHub Pages.
                  </p>
                </div>
              </article>

              <article className="atlas-card overflow-hidden p-3 sm:p-4">
                <LeafletMap className="atlas-map h-[620px] rounded-[28px]" />
              </article>
            </div>
          </div>
        </section>

        <AnalysisSection />

        <section id="methods" className="atlas-section border-y border-[var(--line-soft)] bg-[var(--paper-muted)]">
          <div className="container space-y-12">
            <SectionHeader
              eyebrow="Methods"
              title="A reproducible pipeline shaped around provenance, preservation, and comparability."
              body="The workflow avoids ad hoc scraping and instead gives priority to official products, programmatic discovery, preserved archives, and explicit standardization rules that can be translated to repository scripts and a companion Colab notebook."
            />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <article className="atlas-card atlas-card-tall overflow-hidden">
                <img
                  src={methodsImage}
                  alt="Editorial methods collage combining maps, field notes, environmental samples and analytical plots"
                  className="h-[360px] w-full rounded-[24px] object-cover"
                />
                <div className="mt-8 grid gap-5">
                  {workflow.map((step, index) => (
                    <div key={step.title} className="method-row">
                      <div className="method-index">0{index + 1}</div>
                      <div>
                        <h3 className="font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">{step.title}</h3>
                        <p className="mt-2 text-sm leading-7 text-[var(--ink-soft)]">{step.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <div className="grid gap-6">
                {methodsFigures.map((figure) => (
                  <article key={figure.title} className="atlas-card overflow-hidden">
                    <img src={figure.image} alt={figure.title} className="h-[320px] w-full rounded-[24px] object-cover" />
                    <div className="mt-6 flex items-start gap-4">
                      <Microscope className="mt-1 h-5 w-5 text-[var(--accent-copper)]" />
                      <div>
                        <h3 className="font-[var(--font-display)] text-2xl text-[var(--ink-strong)]">{figure.title}</h3>
                        <p className="mt-2 text-sm leading-7 text-[var(--ink-soft)]">{figure.text}</p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="results" className="atlas-section">
          <div className="container space-y-12">
            <SectionHeader
              eyebrow="Results"
              title="Coverage, quality, and variable availability condensed into a publication-ready comparison layer."
              body="The results section translates repository outputs into a readable synthesis for decision-making. Utility class, acceptable QC share, and standardized variable presence are intentionally shown together so that coverage is never interpreted in isolation."
            />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
              <article className="atlas-card atlas-card-tall bg-[var(--paper-strong)]">
                <p className="section-eyebrow">Comparative summary</p>
                <div className="mt-6 grid gap-5 text-sm leading-7 text-[var(--ink-soft)]">
                  <div className="flex gap-4">
                    <NotebookText className="mt-1 h-5 w-5 text-[var(--accent-forest)]" />
                    <p>
                      The present working inventory spans <strong>{projectStats.stationCount} stations</strong>, <strong>{projectStats.countryCount} countries</strong>, and a common distribution pathway through officially accessible FLUXNET products.
                    </p>
                  </div>
                  <div className="flex gap-4">
                    <Leaf className="mt-1 h-5 w-5 text-[var(--accent-copper)]" />
                    <p>
                      Four stations are currently classified as <strong>high utility</strong>, while two remain in the <strong>medium</strong> class, preserving useful geographic breadth without introducing low-confidence records.
                    </p>
                  </div>
                  <div className="flex gap-4">
                    <MapPinned className="mt-1 h-5 w-5 text-[var(--accent-forest)]" />
                    <p>
                      The strongest score presently belongs to <strong>{projectStats.topSiteId}</strong>, reflecting the best current balance between completeness, QC acceptance, and temporal coverage.
                    </p>
                  </div>
                </div>
              </article>

              <article className="atlas-card overflow-hidden">
                <div className="results-table-wrap">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Site</th>
                        <th>Years</th>
                        <th>Obs.</th>
                        <th>Valid NEE</th>
                        <th>QC</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stationData.map((station) => (
                        <tr key={`row-${station.siteId}`}>
                          <td>
                            <div className="flex flex-col">
                              <span className="font-semibold text-[var(--ink-strong)]">{station.siteId}</span>
                              <span>{station.siteName}</span>
                            </div>
                          </td>
                          <td>{station.yearStart}–{station.yearEnd}</td>
                          <td>{formatNumber(station.observations)}</td>
                          <td>{station.validNeePct.toFixed(1)}%</td>
                          <td>{station.acceptableQcPct.toFixed(1)}%</td>
                          <td>
                            <span
                              className="inline-flex min-w-[84px] items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold"
                              style={{
                                color: station.qualityColor,
                                borderColor: `${station.qualityColor}50`,
                                backgroundColor: `${station.qualityColor}12`,
                              }}
                            >
                              {station.utilityScore.toFixed(3)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section id="about" className="atlas-section border-t border-[var(--line-soft)] bg-[var(--paper-muted)]">
          <div className="container grid gap-8 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <p className="section-eyebrow">About</p>
              <h2 className="font-[var(--font-display)] text-4xl leading-[0.95] text-[var(--ink-strong)] sm:text-5xl">
                Prepared as a publication-ready research interface for environmental data work.
              </h2>
            </div>
            <div className="atlas-card atlas-card-tall">
              <p className="text-base leading-8 text-[var(--ink-soft)]">
                This frontend is part of a broader repository that combines raw FLUXNET archives, standardized station
                outputs, summary tables, and documentation intended for future GitHub publication. The project is prepared
                for <strong>Instituto de Ciencias y Tecnología Ambiental ICTA ltda.</strong>, with <strong>Guillermo S.
                Fuentes-Jaque</strong> as principal consultant.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <a className="atlas-link-card" href="#methods">
                  <span>
                    <span className="section-eyebrow">Workflow</span>
                    <strong>Review the documented processing sequence.</strong>
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </a>
                <a className="atlas-link-card" href="#map">
                  <span>
                    <span className="section-eyebrow">Interactive view</span>
                    <strong>Inspect the regional station distribution.</strong>
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </a>
                <a className="atlas-link-card" href="https://github.com/fluxnet/shuttle" target="_blank" rel="noreferrer">
                  <span>
                    <span className="section-eyebrow">Source tool</span>
                    <strong>Consult the public FLUXNET Shuttle repository.</strong>
                  </span>
                  <ExternalLink className="h-4 w-4" />
                </a>
                <a className="atlas-link-card" href="https://www.icos-cp.eu/data-products" target="_blank" rel="noreferrer">
                  <span>
                    <span className="section-eyebrow">Related portal</span>
                    <strong>Review official ICOS data product descriptions.</strong>
                  </span>
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
