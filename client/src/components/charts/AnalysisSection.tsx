import { AnalysisDashboard } from "@/components/charts/AnalysisDashboard";

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
            A single workbench, organized into tabs: explore standardized daily fluxes and meteorology, compare
            distributions across stations, read the regional map, and assess each station's ecological and
            climate-space representativeness — which conditions it samples and how much of the Southern Cone it stands
            in for.
          </p>
        </div>

        <AnalysisDashboard />
      </div>
    </section>
  );
}
