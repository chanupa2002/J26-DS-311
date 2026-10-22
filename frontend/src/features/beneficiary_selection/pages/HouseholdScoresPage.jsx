import { useEffect, useRef, useState } from "react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { beneficiaryApi } from "../api"
import { GlossaryEntry } from "../components/ResearchPageFrame"

const nodeNames = [
  ["Living conditions", "living_conditions"],
  ["Sensitivity", "sensitivity"],
  ["Adaptive capacity", "adaptive_capacity"],
  ["Overall vulnerability", "vulnerability"],
]
const inputNames = {
  food: "Food insecurity", crowding: "Crowding", dependency: "Dependency",
  income: "Household income", assets: "Household assets", tenure: "Tenure security",
  toilet: "Sanitation service", wall: "Wall material", floor: "Floor material",
  roof: "Roof material", bank_account: "Bank account access", has_debt: "Household debt",
  health: "Health",
}
const fixed = (value, digits = 3) => value == null ? "Unavailable" : Number(value).toFixed(digits)
const percent = (value) => value == null ? "Unavailable" : `${(Number(value) * 100).toFixed(1)}%`
const definitions = [
  ["Rank position", "rank_position"],
  ["Vulnerability level", "vulnerability_level"],
  ["High-vulnerability estimate", "high_vulnerability_estimate"],
  ["Evidence used", "evidence_used"],
  ["Comparison group", "comparison_group"],
  ["Sensitivity run", "sensitivity_run"],
  ["Rank correlation", "rank_correlation"],
  ["Households changing level", "level_change"],
  ["Research output", "research_output"],
]

export function HouseholdsPage() {
  const [filters, setFilters] = useState({ province: "", district: "" })
  const [appliedFilters, setAppliedFilters] = useState({ province: "", district: "" })
  const [range, setRange] = useState([0, 100])
  const [brush, setBrush] = useState(null)
  const [page, setPage] = useState(0)
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [geography, setGeography] = useState({ provinces: [], districts: [] })
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const chartRef = useRef(null)
  const dragStart = useRef(null)

  async function load(nextPage = 0, nextFilters = filters, nextRange = range) {
    setLoading(true)
    setError(null)
    try {
      const response = await beneficiaryApi.households({ ...nextFilters, min_percentile: nextRange[0], max_percentile: nextRange[1], offset: nextPage * 50, limit: 50 })
      setData(response)
      setAppliedFilters({ ...nextFilters })
      setPage(nextPage)
    } catch (loadError) { setError(loadError) } finally { setLoading(false) }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => load(0), 0)
    beneficiaryApi.summary().then(setSummary).catch(setError)
    beneficiaryApi.geography().then(setGeography).catch(setError)
    return () => window.clearTimeout(timer)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const bins = summary?.expected_vulnerability_histogram || []
  const minScore = bins.length ? bins[0].score_min : 0
  const maxScore = bins.length ? bins[bins.length - 1].score_max : 1
  const xOf = (score) => 50 + ((Number(score) - minScore) / Math.max(maxScore - minScore, 1e-9)) * 900
  const provinceNames = Object.fromEntries(geography.provinces.map((item) => [String(item.code), item.name]))
  const districtNames = Object.fromEntries(geography.districts.map((item) => [String(item.code), item.name]))
  const availableDistricts = geography.districts.filter((item) => !filters.province || String(item.province_code) === filters.province)

  function scoreAt(event) {
    const rect = chartRef.current.getBoundingClientRect()
    const relative = Math.max(50, Math.min(950, ((event.clientX - rect.left) / rect.width) * 1000))
    return minScore + ((relative - 50) / 900) * (maxScore - minScore)
  }

  function brushToRange(start, end) {
    if (!bins.length) return
    const low = Math.min(start, end)
    const high = Math.max(start, end)
    const chosen = bins.filter((bin) => bin.score_max >= low && bin.score_min <= high)
    const selected = chosen.length ? chosen : [bins.reduce((best, bin) => Math.abs((bin.score_min + bin.score_max) / 2 - low) < Math.abs((best.score_min + best.score_max) / 2 - low) ? bin : best, bins[0])]
    const next = [
      Math.max(0, Math.floor(Math.min(...selected.map((bin) => bin.percentile_min)))),
      Math.min(100, Math.ceil(Math.max(...selected.map((bin) => bin.percentile_max)))),
    ]
    setRange(next)
    setBrush([low, high])
    load(0, filters, next)
  }

  const displayScope = appliedFilters.district
    ? `${districtNames[appliedFilters.district] || "Selected district"}, ${provinceNames[appliedFilters.province] || "selected province"}`
    : appliedFilters.province ? provinceNames[appliedFilters.province] || "Selected province" : "All saved baseline household records"

  return <div className="space-y-5">
    <PageHeader title="Household Scores" description="Explore saved household model scores and the evidence behind them." />
    <DistributionCard bins={bins} xOf={xOf} range={range} brush={brush} chartRef={chartRef} onKeyDown={(event) => { if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); const delta = event.key === "ArrowLeft" ? -5 : 5; const next = [Math.max(0, Math.min(95, range[0] + delta)), Math.max(5, Math.min(100, range[1] + delta))]; setRange(next); load(0, filters, next) } }} onClear={() => { setBrush(null); setRange([0, 100]); load(0, filters, [0, 100]) }} onPointerDown={(event) => { if (bins.length) { event.currentTarget.setPointerCapture(event.pointerId); dragStart.current = scoreAt(event); setBrush([dragStart.current, dragStart.current]) } }} onPointerMove={(event) => { if (dragStart.current != null) setBrush([dragStart.current, scoreAt(event)]) }} onPointerUp={(event) => { if (dragStart.current != null) { const start = dragStart.current; dragStart.current = null; brushToRange(start, scoreAt(event)) } }} />
    <Card><CardContent className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
      <label className="space-y-1 text-sm">Province<select className="h-9 w-full rounded-md border bg-background px-3" value={filters.province} onChange={(event) => setFilters({ province: event.target.value, district: "" })}><option value="">All provinces</option>{geography.provinces.map((item) => <option key={item.code} value={String(item.code)}>{item.name}</option>)}</select></label>
      <label className="space-y-1 text-sm">District<select className="h-9 w-full rounded-md border bg-background px-3" value={filters.district} disabled={!geography.districts.length} onChange={(event) => setFilters({ ...filters, district: event.target.value })}><option value="">All districts</option>{availableDistricts.map((item) => <option key={item.code} value={String(item.code)}>{item.name}</option>)}</select></label>
      <div className="flex items-end"><Button onClick={() => load(0, filters, range)} disabled={loading}>{loading ? "Loading…" : "Apply filters"}</Button></div>
    </CardContent></Card>
    {error && <p role="alert" className="rounded-md border p-3 text-sm">{error.message || String(error)}</p>}
    {data && <>
      <div className="space-y-1"><p className="text-sm font-medium">Percentile comparison group: All saved baseline household records ({summary?.household_count?.toLocaleString() || "count unavailable"}).</p><p className="text-sm text-muted-foreground">Displayed records: {displayScope} ({data.total.toLocaleString()} matching records). Percentile ranks remain calculated against the full saved baseline, even when location filters are applied. Every score row includes its evidence-used count.</p><p className="text-sm text-muted-foreground">Selected percentile range: {range[0]} to {range[1]}.</p></div>
      <div className="overflow-x-auto rounded-xl border"><Table><TableHeader><TableRow>
        <Header title="Record" id="record"/><Header title="Province" id="province"/><Header title="District" id="district"/><Header title="Rank position" id="rank_position"/><Header title="Vulnerability level" id="vulnerability_level"/><Header title="Model estimate of high vulnerability" id="high_vulnerability_estimate"/><Header title="Evidence used" id="evidence_used"/><Header title="Explain" id="explain_result"/>
      </TableRow></TableHeader><TableBody>{data.items.map((row) => <TableRow key={row.row_id} className={selected?.item?.row_id === row.row_id ? "bg-muted" : ""}>
        <TableCell>{row.row_id}</TableCell><TableCell>{provinceNames[String(row.province)] || "Unknown code"}</TableCell><TableCell>{districtNames[String(row.district)] || "Unknown code"}</TableCell><TableCell>{fixed(row.percentile_rank, 1)}</TableCell><TableCell>{fixed(row.bn_expected_vulnerability)}</TableCell><TableCell>{percent(row.bn_p_high)}</TableCell><TableCell>{row.evidence_n_used == null ? "Unavailable" : `${row.evidence_n_used} of ${row.evidence_n_total} model inputs`}</TableCell><TableCell><Button size="sm" variant="outline" onClick={async () => { try { setSelected(await beneficiaryApi.household(row.row_id)) } catch (loadError) { setError(loadError) } }}>Explain</Button></TableCell>
      </TableRow>)}</TableBody></Table></div>
      {selected?.item && <ScoreExplanation response={selected} comparisonGroup="All saved baseline household records" onClose={() => setSelected(null)} />}
      <div className="flex gap-2"><Button variant="outline" disabled={page === 0 || loading} onClick={() => load(page - 1)}>Previous</Button><Button variant="outline" disabled={loading || (page + 1) * 50 >= data.total} onClick={() => load(page + 1)}>Next</Button></div>
    </>}
  </div>
}

function DistributionCard({ bins, xOf, range, brush, chartRef, onClear, onPointerDown, onPointerMove, onPointerUp, onKeyDown }) {
  const maxCount = Math.max(...bins.map((bin) => bin.households_n), 1)
  const left = brush ? xOf(Math.min(...brush)) : 0
  const right = brush ? xOf(Math.max(...brush)) : 0
  return <Card><CardHeader className="flex-row items-center justify-between gap-3"><div><CardTitle className="text-base">Expected vulnerability distribution</CardTitle><p className="mt-1 text-sm text-muted-foreground">Comparison group: saved baseline household records. Each bar shows an unweighted record count. Drag across the chart to filter by its percentile range.</p></div><Button size="sm" variant="outline" onClick={onClear}>Clear range</Button></CardHeader><CardContent>
    {bins.length ? <><svg ref={chartRef} viewBox="0 0 1000 240" role="slider" aria-label="Drag across expected vulnerability scores to filter the comparison percentile range" aria-valuetext={`${range[0]} to ${range[1]} percentile`} aria-valuemin="0" aria-valuemax="100" aria-valuenow={range[0]} tabIndex={0} className="block h-auto w-full touch-none select-none cursor-crosshair focus-visible:outline-2 focus-visible:outline-ring" onKeyDown={onKeyDown} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}>
      <line x1="50" y1="195" x2="950" y2="195" stroke="currentColor" strokeOpacity=".35"/>
      {bins.map((bin, index) => { const width = 900 / bins.length; const height = 145 * bin.households_n / maxCount; return <g key={`${bin.score_min}-${index}`}><rect x={50 + index * width + 2} y={195 - height} width={Math.max(2, width - 4)} height={height} rx="3" fill="hsl(var(--muted-foreground))" fillOpacity=".62"><title>{bin.households_n.toLocaleString()} records; score {bin.score_min.toFixed(3)} to {bin.score_max.toFixed(3)}; percentile {bin.percentile_min.toFixed(1)} to {bin.percentile_max.toFixed(1)}</title></rect><text x={50 + index * width + width / 2} y="215" textAnchor="middle" fontSize="10" fill="currentColor">{bin.score_min.toFixed(2)}</text></g> })}
      {bins.length > 0 && <text x="500" y="238" textAnchor="middle" fontSize="12" fill="currentColor">Vulnerability level (0 to 1)</text>}
      {brush && <rect x={left} y="28" width={Math.max(2, right - left)} height="169" fill="hsl(var(--primary))" fillOpacity=".12" stroke="hsl(var(--primary))"/>}
    </svg><p className="text-xs text-muted-foreground">Selected percentile range: {range[0]} to {range[1]}. Use arrow keys after focusing the chart to move its selection.</p><GlossaryEntry id="comparison_group" showShort/></> : <p className="text-sm text-muted-foreground">Distribution is unavailable. Its comparison group and evidence coverage are shown in the page context.</p>}
  </CardContent></Card>
}

function Header({ title, id }) {
  return <TableHead><span className="inline-flex items-center gap-1">{title}<GlossaryEntry id={id}/></span></TableHead>
}

function ScoreExplanation({ response, comparisonGroup, onClose }) {
  const item = response.item
  const memberships = item.input_memberships || {}
  const unknowns = Object.entries(memberships).filter(([, value]) => value == null).map(([key]) => inputNames[key] || key.replaceAll("_", " "))
  const values = Object.entries(memberships)
  const nodes = item.domain_posteriors || {}
  return <Card><CardHeader className="flex-row items-center justify-between gap-3"><div><CardTitle>Score explanation · record {item.row_id}</CardTitle><p className="mt-1 text-sm text-muted-foreground">{response.research_label}. Model {response.model_version}; spec {response.spec_version}; data {response.data_manifest_sha256?.slice(0, 10) || "unavailable"}.</p></div><Button variant="ghost" onClick={onClose}>Close</Button></CardHeader><CardContent className="space-y-5">
    <p className="text-sm">Comparison group: {comparisonGroup} ({response.baseline_household_count?.toLocaleString() || "count unavailable"} saved records).</p>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Metric title="Vulnerability level (0 to 1)" value={fixed(item.bn_expected_vulnerability)} help="Higher values mean higher modeled vulnerability."/><Metric title="Model estimate of high vulnerability" value={percent(item.bn_p_high)} help="Expert-rule model estimate; it has not been calibrated against real outcomes."/><Metric title="Rank position" value={`${fixed(item.percentile_rank, 1)}th`} help="Relative position within the comparison group, not a probability."/><Metric title="Evidence used" value={item.evidence_n_used == null ? "Unavailable" : `${item.evidence_n_used} of ${item.evidence_n_total} inputs`} help="Available model inputs recorded for this household."/></div>
    <section className="space-y-3"><h3 className="font-semibold">Low, medium, and high model probabilities</h3><p className="text-sm text-muted-foreground">Each network level has a probability distribution. A household may have probability across all three states at once.</p>{nodeNames.map(([title, key]) => <ProbabilityBar key={key} title={title} values={nodes[key]}/>)}</section>
    <section className="space-y-2"><h3 className="font-semibold">Available evidence by model input</h3><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(item.domain_coverage || {}).map(([key, value]) => <div className="rounded-md border p-2 text-sm" key={key}><span>{key.replaceAll("_", " ")}</span><span className="float-right font-medium">{value.n_used == null ? "Unknown" : `${value.n_used} of ${value.n_total}`}</span></div>)}</div></section>
    <section className="space-y-2"><h3 className="font-semibold">Input memberships</h3><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{values.map(([key, value]) => <div className="rounded-md border p-2 text-sm" key={key}><span>{inputNames[key] || key.replaceAll("_", " ")}</span><span className="float-right font-medium">{value == null ? "Unknown" : Number(value).toFixed(3)}</span></div>)}</div>{unknowns.length > 0 && <p className="text-sm text-muted-foreground">Unknown inputs: {unknowns.join(", ")}.</p>}{unknowns.length === 0 && <p className="text-sm text-muted-foreground">No unavailable fuzzy memberships are flagged. This describes model inputs, not whether every raw survey answer was recorded.</p>}</section>
    <section className="rounded-lg bg-muted/50 p-3 text-sm"><h3 className="font-semibold">Interpretation</h3><p className="mt-1">Read the expected vulnerability level, probability distribution, rank position, and evidence-used count together. Fewer available inputs mean less evidence supports the estimate. This score is a research result, not an eligibility decision.</p></section>
    <section className="space-y-1"><h3 className="font-semibold">Range across saved sensitivity runs</h3><p className="text-sm text-muted-foreground">Expected level: {fixed(item.sensitivity_expected_min)} to {fixed(item.sensitivity_expected_max)}. Rank position: {fixed(item.sensitivity_rank_min, 1)} to {fixed(item.sensitivity_rank_max, 1)}. This is a sensitivity range, not a posterior interval.</p></section>
  </CardContent></Card>
}

function Metric({ title, value, help }) {
  return <div className="rounded-lg border p-3"><p className="text-xs font-medium text-muted-foreground">{title}</p><p className="mt-1 text-xl font-semibold">{value}</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{help}</p></div>
}

function ProbabilityBar({ title, values = {} }) {
  const colors = ["bg-slate-300 dark:bg-slate-600", "bg-slate-500 dark:bg-slate-400", "bg-indigo-500 dark:bg-indigo-300"]
  return <div><div className="mb-1 flex flex-wrap justify-between gap-1 text-xs"><span className="font-medium">{title}</span><span className="text-muted-foreground">{[["low", "Low"], ["medium", "Medium"], ["high", "High"]].map(([key, label]) => `${label}: ${percent(values[key])}`).join(" · ")}</span></div><div className="flex h-3 overflow-hidden rounded-full bg-muted" aria-label={`${title}: Low ${percent(values.low)}, Medium ${percent(values.medium)}, High ${percent(values.high)}`}>{[["low", 0], ["medium", 1], ["high", 2]].map(([key, index]) => <div key={key} className={colors[index]} style={{ width: `${Math.max(0, Math.min(1, Number(values[key]) || 0)) * 100}%` }}/>)}</div></div>
}

export function MethodPage() {
  return <div id="changelog" className="space-y-5"><PageHeader title="Method & Limits" description="How the research model turns survey inputs into saved estimates, and what those estimates can and cannot say."/><Card><CardHeader><CardTitle>What the current model does</CardTitle></CardHeader><CardContent><ol className="list-decimal space-y-2 pl-5 text-sm"><li>Survey fields are converted into fuzzy model inputs using frozen reference values and the current v0.2 interim rules.</li><li>The eight baseline input leaves become low, medium, and high soft memberships.</li><li>The Bayesian network combines these memberships through living conditions, sensitivity, and adaptive capacity.</li><li>The output is a vulnerability level, state probabilities, and a position relative to the saved comparison group.</li></ol><p className="mt-3 text-sm text-muted-foreground">No model rules or scoring tables are changed by this interface.</p></CardContent></Card>
    <Card><CardHeader><CardTitle>Definitions</CardTitle></CardHeader><CardContent className="space-y-4">{definitions.map(([title, id]) => <section key={id}><h3 className="font-semibold">{title} <GlossaryEntry id={id}/></h3></section>)}<p><GlossaryEntry id="unknown_vs_no" showShort/></p><p><GlossaryEntry id="soft_levels" showShort/></p><p><GlossaryEntry id="domain_housing" showShort/></p><p><GlossaryEntry id="domain_economic" showShort/></p><p><GlossaryEntry id="domain_food" showShort/></p><p><GlossaryEntry id="domain_demographic" showShort/></p></CardContent></Card>
    <Card><CardHeader><CardTitle>Limitations</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-2 pl-5 text-sm"><li>Probabilities come from expert-set rules and are not validated against real outcomes.</li><li><code>label_high_vuln</code> is a proxy reference, not ground truth.</li><li>Wall, floor, and roof ratings use an interim rule (D-03a).</li><li>Some inputs are missing for some households; for example, income is unavailable for about 22% in the current analysis.</li><li>The two food-insecurity forms are still being checked for comparability.</li><li>The survey is from 2025 and is not updated here.</li><li>Domain weights are equal by default and remain under sensitivity review.</li><li>The tool is not designed for eligibility decisions.</li></ul></CardContent></Card>
    <DecisionLog/><div className="space-y-1"><h2 className="text-lg font-semibold">Changelog</h2><p className="text-sm text-muted-foreground">This page records the usability and explainability changes for the research prototype.</p><ul className="list-disc pl-5 text-sm"><li>Added plain-language overview, glossary popovers, location names, and evidence coverage.</li><li>Grouped candidate and CSV scoring under Assess a Household; legacy links redirect.</li></ul></div>
  </div>
}

function DecisionLog() {
  const [data, setData] = useState(null)
  useEffect(() => { beneficiaryApi.spec().then(setData).catch(() => setData(null)) }, [])
  return <Card><CardHeader><CardTitle>Decision log</CardTitle><p className="text-sm text-muted-foreground">Authoritative source decisions are available from the API.</p></CardHeader><CardContent>{data?.documents?.length ? <details><summary className="cursor-pointer text-sm font-medium">Read source decision documents</summary>{data.documents.map((doc) => <details className="mt-3" key={doc.filename}><summary className="cursor-pointer text-sm">{doc.filename}</summary><pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-xs">{doc.content}</pre></details>)}</details> : <p className="text-sm text-muted-foreground">Decision documents are unavailable.</p>}</CardContent></Card>
}
