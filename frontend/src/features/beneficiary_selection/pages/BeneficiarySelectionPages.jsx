import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { API_URL } from "@/lib/env"
import { api } from "@/lib/api"
import { beneficiaryApi } from "../api"
import { GlossaryEntry } from "../components/ResearchPageFrame"

const label = "Research output - not an eligibility determination"
const leaves = [
  ["shelter_quality", "Shelter quality", "Condition of the household's walls, floor, and roof. Higher values indicate more vulnerability from less durable shelter materials."],
  ["sanitation", "Sanitation", "Access to and condition of toilet facilities, including whether facilities are shared. Higher values indicate more sanitation deprivation."],
  ["crowding_tenure", "Crowding and tenure", "Crowding in the home and security of the household's right to stay there. Higher values indicate greater housing pressure or less secure tenure."],
  ["food", "Food security", "Household experiences of difficulty getting enough food. Higher values indicate more food insecurity."],
  ["demographic", "Demographic vulnerability", "Dependency within the household, based on younger and older members relative to working-age members. Higher values indicate greater dependency pressure."],
  ["health", "Health", "Share of household members reported with chronic illness or severe disability. Higher values indicate greater health-related vulnerability."],
  ["economic", "Economic conditions", "Household income and assets used by the model as indicators of economic capacity. Higher values indicate greater economic vulnerability."],
  ["financial_resilience", "Financial resilience", "Financial access and debt indicators used by the model. Higher values indicate weaker financial resilience in this model."],
]

function ErrorNotice({ error }) {
  return error ? <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm">{error.message || String(error)}</p> : null
}

function ResearchNotice() {
  return <p className="text-xs text-muted-foreground">{label}</p>
}

function fixed(value, digits = 3) {
  return value == null ? "â€”" : Number(value).toFixed(digits)
}

function percent(value) {
  return value == null ? "â€”" : `${(Number(value) * 100).toFixed(1)}%`
}

export function HouseholdsPage() {
  const [filters, setFilters] = useState({ province: "", district: "", min_percentile: "", max_percentile: "" })
  const [page, setPage] = useState(0)
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const load = async (nextPage = page) => {
    setBusy(true); setError(null)
    try { setData(await beneficiaryApi.households({ ...filters, offset: nextPage * 50, limit: 50 })); setPage(nextPage) }
    catch (e) { setError(e) } finally { setBusy(false) }
  }
  useEffect(() => { load(0) }, []) // eslint-disable-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  return <div className="space-y-5">
    <PageHeader title="Ranked Households" description="Browse saved model results with filters and pagination." />
    <ResearchNotice />
    <Card><CardContent className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
      {[["province", "Province"], ["district", "District"], ["min_percentile", "Minimum percentile"], ["max_percentile", "Maximum percentile"]].map(([key, name]) => <label key={key} className="space-y-1 text-sm">{name}<input className="h-9 w-full rounded-md border bg-background px-3" value={filters[key]} onChange={e => setFilters({ ...filters, [key]: e.target.value })} /></label>)}
      <div className="flex items-end"><Button onClick={() => load(0)} disabled={busy}>{busy ? "Loadingâ€¦" : "Apply filters"}</Button></div>
    </CardContent></Card>
    <ErrorNotice error={error} />
    {data && <>
      <p className="text-sm text-muted-foreground">{data.total} matching records Â· page {page + 1}</p>
      <div className="rounded-xl border"><Table><TableHeader><TableRow>{["Record", "Province", "District", "Model percentile", "Expected vulnerability index", "Chance of high vulnerability", "Explanation"].map(x => <TableHead key={x}>{x}</TableHead>)}</TableRow></TableHeader><TableBody>{data.items.map(row => <TableRow key={row.row_id}><TableCell>{row.row_id}</TableCell><TableCell>{row.province ?? "â€”"}</TableCell><TableCell>{row.district ?? "â€”"}</TableCell><TableCell>{fixed(row.percentile_rank, 1)}</TableCell><TableCell>{fixed(row.bn_expected_vulnerability)}</TableCell><TableCell>{percent(row.bn_p_high)}</TableCell><TableCell><Button size="sm" variant="outline" onClick={async () => { try { setSelected(await beneficiaryApi.household(row.row_id)) } catch (e) { setError(e) } }}>Explain result</Button></TableCell></TableRow>)}</TableBody></Table></div>
      {selected?.item && <ScoreExplanation item={selected.item} onClose={() => setSelected(null)} />}
      <div className="flex gap-2"><Button variant="outline" disabled={page === 0 || busy} onClick={() => load(page - 1)}>Previous</Button><Button variant="outline" disabled={busy || (page + 1) * 50 >= data.total} onClick={() => load(page + 1)}>Next</Button></div>
    </>}
  </div>
}

function ScoreExplanation({ item, onClose }) {
  const probabilities = [
    ["Low", item.bn_vulnerability_low],
    ["Medium", item.bn_vulnerability_medium],
    ["High", item.bn_vulnerability_high],
  ]
  return <Card>
    <CardHeader><div className="flex items-center justify-between gap-4"><div><CardTitle>Model result explanation Â· record {item.row_id}</CardTitle><p className="mt-2 text-sm text-muted-foreground">These are model estimates for this record. They are not an eligibility decision.</p></div><Button size="sm" variant="ghost" onClick={onClose}>Close</Button></div></CardHeader>
    <CardContent className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric title="Expected vulnerability index" value={fixed(item.bn_expected_vulnerability)} help="Model's expected level on a 0â€“1 scale; larger values mean a higher modeled level." />
        <Metric title="Chance of high vulnerability" value={percent(item.bn_p_high)} help="Model-estimated probability of the high state." />
        <Metric title="Model percentile" value={`${fixed(item.percentile_rank, 1)}th`} help="Relative position among the saved household scores. It is not a national poverty percentile." />
        <Metric title="Domain information available" value={`${item.bn_leaves_observed ?? "â€”"} of ${item.bn_leaves_total ?? "â€”"}`} help="Number of model domains with observed input information." />
      </div>
      <section className="space-y-2"><h4 className="text-sm font-semibold">Model probability by vulnerability level</h4><div className="grid gap-2 sm:grid-cols-3">{probabilities.map(([name, value]) => <div key={name} className="rounded-lg border p-3"><p className="text-sm text-muted-foreground">{name}</p><p className="text-lg font-semibold">{percent(value)}</p></div>)}</div></section>
      <section className="space-y-1 rounded-lg bg-muted/50 p-3 text-sm"><h4 className="font-semibold">How to read these numbers</h4><p>The expected index summarizes the model's probability across its low, medium, and high states. The high-vulnerability chance is the probability assigned to the high state. The percentile compares this model score with the saved scores in the dataset.</p><p>Use the domain count and sensitivity range as context. Neither the score nor the percentile should be used by itself to determine eligibility or assistance.</p></section>
      <section className="space-y-2"><h4 className="text-sm font-semibold">Range across saved sensitivity runs</h4><p className="text-sm text-muted-foreground">Expected index: {fixed(item.sensitivity_expected_min)} to {fixed(item.sensitivity_expected_max)} Â· percentile: {fixed(item.sensitivity_rank_min, 1)} to {fixed(item.sensitivity_rank_max, 1)}</p></section>
    </CardContent>
  </Card>
}

function Metric({ title, value, help }) {
  return <div className="rounded-lg border p-3"><p className="text-xs font-medium text-muted-foreground">{title}</p><p className="mt-1 text-xl font-semibold">{value}</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{help}</p></div>
}

export function LegacyCandidateScoringPage() {
  const initial = Object.fromEntries(leaves.map(([key]) => [key, { degree: "", coverage_fraction: "1" }]))
  const [values, setValues] = useState(initial)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError(null); setResult(null)
    try {
      const input = Object.fromEntries(leaves.map(([key]) => {
        const value = values[key]
        return [key, { degree: value.degree === "" ? "unobserved" : Number(value.degree), coverage_fraction: value.degree === "" ? 0 : Number(value.coverage_fraction) }]
      }))
      setResult(await beneficiaryApi.score(input))
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  return <div className="space-y-5">
    <PageHeader title="Score a Candidate" description="Enter domain degrees and coverage to request a temporary what-if result." />
    <ResearchNotice />
    <Card><CardHeader className="pb-2"><CardTitle className="text-base">How to enter the scores</CardTitle></CardHeader><CardContent className="space-y-2 text-sm text-muted-foreground">
      <p><strong className="text-foreground">Degree (0 to 1):</strong> this is a vulnerability or deprivation score. 0 means none or lowest indicated vulnerability; 1 means highest indicated vulnerability. For example, a higher shelter score means less durable shelter materials. Use values between these endpoints when the evidence is mixed.</p>
      <p><strong className="text-foreground">Coverage fraction (0 to 1):</strong> how much of the information needed for that domain is available. 1 means all expected information is available; 0.5 means about half; 0 means none. Leave the degree blank when the domain was not observed; blank is not the same as 0.</p>
      <p>The degree is an input to the model, not a percentage of people affected. All domains are vulnerability-oriented: higher values point toward greater modeled vulnerability.</p>
    </CardContent></Card>
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">{leaves.map(([key, title, description]) => <Card key={key}><CardHeader className="pb-3"><CardTitle className="text-base">{title}</CardTitle><p className="text-sm text-muted-foreground">{description}</p></CardHeader><CardContent className="grid grid-cols-2 gap-3">
        <label className="space-y-1 text-sm">Degree (0â€“1; blank = unobserved)<input type="number" min="0" max="1" step="any" value={values[key].degree} onChange={e => setValues({ ...values, [key]: { ...values[key], degree: e.target.value } })} className="h-9 w-full rounded-md border bg-background px-3" /></label>
        <label className="space-y-1 text-sm">Coverage fraction<input type="number" min="0" max="1" step="any" value={values[key].coverage_fraction} disabled={values[key].degree === ""} onChange={e => setValues({ ...values, [key]: { ...values[key], coverage_fraction: e.target.value } })} className="h-9 w-full rounded-md border bg-background px-3 disabled:opacity-50" /></label>
      </CardContent></Card>)}</div>
      <Button type="submit" disabled={busy}>{busy ? "Scoringâ€¦" : "Score candidate"}</Button>
    </form>
    <ErrorNotice error={error} />
    {result && <WhatIfResult result={result} />}
  </div>
}

const assessmentAssetCounts = ["d_01", "d_03", "d_05", "d_06", "d_08", "d_10", "d_17", "d_18", "d_19", "d_20", "d_21", "d_22", "d_23"]
const assessmentAssetBinary = ["d_12", "d_13", "d_14", "d_15", "d_16"]
const assessmentAssetFields = [...assessmentAssetCounts, ...assessmentAssetBinary]
const makeAssessment = () => ({
  roster_ages: [], bedrooms: null, wall_code: null, floor_code: null, roof_code: null,
  tenure_code: null, toilet_code: null, toilet_shared: null, monthly_income: null,
  assets: Object.fromEntries(assessmentAssetFields.map((field) => [field, null])),
  food_answers: Array(8).fill(null),
})
const materialOptions = {
  wall_code: [[1,"Brick"],[2,"Cement block"],[3,"Stone"],[4,"Cabook"],[5,"Clay"],[6,"Cadjan/Palmyrah"],[7,"Wood"],[8,"Asbestos"],[9,"Cloth"],[10,"Polythene"],[11,"Metal sheet/Takaran"],[999,"Other"]],
  floor_code: [[1,"Cement"],[2,"Terrazzo/Tile/Granite"],[3,"Mud"],[4,"Wood"],[5,"Sand"],[6,"Concrete"],[7,"Metal"],[999,"Other"]],
  roof_code: [[1,"Tile"],[2,"Asbestos"],[3,"Concrete"],[4,"Metal sheet"],[5,"Takaran"],[6,"Cadjan/Palmyrah/Straw"],[7,"Polythene"],[999,"Other"]],
  tenure_code: [[1,"Owned group, code 1"],[2,"Owned group, code 2"],[3,"Owned group, code 3"],[4,"Rented"],[5,"Gift"],[6,"Rent-free"],[7,"Encroached"],[8,"Temporary"],[999,"Other / Unknown"]],
  toilet_code: [...Array.from({length:14},(_,i)=>[i+1,`Code ${i+1} (questionnaire label TODO)`]),[999,"Other / Unknown"]],
  toilet_shared: [[0,"Not shared"],[1,"Shared"]],
}

export function CandidateScoringPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get("tab") === "csv" ? "csv" : "single"
  return <div className="space-y-5"><PageHeader title="Assess a Household" description="Enter coded questionnaire answers for a temporary estimate, or preview a CSV batch before scoring."/><Tabs value={tab} onValueChange={(value) => setSearchParams({ tab: value })}><TabsList aria-label="Assessment input type"><TabsTrigger value="single">Single record</TabsTrigger><TabsTrigger value="csv">CSV batch</TabsTrigger></TabsList><TabsContent value="single"><RawAssessmentForm/></TabsContent><TabsContent value="csv"><BulkScoringPage embedded/></TabsContent></Tabs></div>
}

function RawAssessmentForm() {
  const [answers, setAnswers] = useState(makeAssessment)
  const [statuses, setStatuses] = useState({})
  const [agesText, setAgesText] = useState("")
  const [ageError, setAgeError] = useState("")
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (ageError) return undefined
    let active = true
    const timer = setTimeout(() => beneficiaryApi.derive(answers).then((value) => { if (active) setPreview(value) }).catch((reason) => { if (active) setError(reason) }), 350)
    return () => { active = false; clearTimeout(timer) }
  }, [answers, ageError])

  function setSimple(key, value) {
    const status = value === "__dk" ? "dont_know" : value === "__refused" ? "refused" : value === "" ? "not_answered" : "answered"
    setStatuses((prior) => ({ ...prior, [key]: status }))
    setAnswers((prior) => ({ ...prior, [key]: status === "answered" ? Number(value) : null }))
  }
  function setCode(key, selected) {
    const status = selected === "__dk" ? "dont_know" : selected === "__refused" ? "refused" : selected === "" ? "not_answered" : "answered"
    setStatuses((prior) => ({ ...prior, [key]: status }))
    setAnswers((prior) => ({ ...prior, [key]: status === "answered" ? Number(selected) : null }))
  }
  function choice(key, current) { return statuses[key] === "dont_know" ? "__dk" : statuses[key] === "refused" ? "__refused" : current == null ? "" : String(current) }
  function setAsset(key, value) {
    const status = value === "__dk" ? "dont_know" : value === "__refused" ? "refused" : value === "" ? "not_answered" : "answered"
    setStatuses((prior) => ({ ...prior, [key]: status }))
    setAnswers((prior) => ({ ...prior, assets: { ...prior.assets, [key]: status === "answered" ? Number(value) : null } }))
  }
  function updateAges(text) {
    setAgesText(text)
    if (!text.trim()) { setAgeError(""); setAnswers((prior) => ({ ...prior, roster_ages: [] })); return }
    const tokens = text.split(",").map((part) => part.trim())
    const parsed = tokens.map((part) => part === "?" ? null : Number(part))
    if (parsed.some((age) => age !== null && (!Number.isInteger(age) || age < 0))) { setAgeError("Enter whole-number ages separated by commas; use ? for an unknown age."); return }
    setAgeError(""); setAnswers((prior) => ({ ...prior, roster_ages: parsed }))
  }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(null); setResult(null)
    try { setResult(await beneficiaryApi.assess(answers)) } catch (reason) { setError(reason) } finally { setBusy(false) }
  }
  const coded = (key, title, help) => <InputCodeField key={key} title={title} help={help} options={materialOptions[key]} value={choice(key, answers[key])} onChange={(value) => setCode(key, value)}/>

  return <form onSubmit={submit} className="space-y-4">
    <Card><CardHeader><CardTitle className="text-base">Household roster and housing</CardTitle><p className="text-sm text-muted-foreground">Enter raw answers; the backend applies existing derivation rules. Unavailable question wording is marked TODO.</p></CardHeader><CardContent className="grid gap-4 md:grid-cols-2">
      <InputField title="Roster ages in years" help="Enter ages separated by commas; use ? when an age is unknown. Ages entered here are treated as the household roster for this temporary estimate."><input className="h-9 w-full rounded-md border bg-background px-3" value={agesText} onChange={(event) => updateAges(event.target.value)} placeholder="Example: 35, 12, 68" aria-invalid={Boolean(ageError)}/>{ageError && <span role="alert" className="text-xs">{ageError}</span>}</InputField>
      <NumberInput title="Number of bedrooms (C1_02)" value={answers.bedrooms} status={statuses.bedrooms} min="0" step="1" onChange={(value) => setSimple("bedrooms", value)} help="Enter the recorded number; zero leaves persons per bedroom unknown."/>
      {coded("wall_code", "Wall material (C1_04)")}{coded("floor_code", "Floor material (C1_05)")}{coded("roof_code", "Roof material (C1_06)")}{coded("tenure_code", "Tenure (C1_07)")}{coded("toilet_code", "Toilet type (C1_08)", "The source questionnaire labels for codes 1 to 14 are unavailable. Codes 5 and 10 remain Unknown pending confirmation.")}{coded("toilet_shared", "Toilet shared (C1_10)", "Cleaned-file codes: 0 = not shared, 1 = shared.")}
      <NumberInput title="Total monthly household income (H1_17)" value={answers.monthly_income} status={statuses.monthly_income} min="0" step="any" onChange={(value) => setSimple("monthly_income", value)} help="Enter the household total monthly value; the existing frozen income reference is used."/>
    </CardContent></Card>
    <Card><CardHeader><CardTitle className="text-base">Household assets</CardTitle><p className="text-sm text-muted-foreground">The cleaned-file codebook lists 18 items: count fields and five yes/no fields. Item-specific question labels are TODO because the data dictionary was not supplied.</p></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{assessmentAssetFields.map((field, index) => assessmentAssetCounts.includes(field) ? <NumberInput key={field} title={`Asset item ${index + 1} count (wording TODO)`} value={answers.assets[field]} min="0" step="1" onChange={(value) => setAsset(field, value)} help="Enter a non-negative count, or choose an unknown response." status={choice(field, answers.assets[field])}/ > : <InputCodeField key={field} title={`Asset item ${index + 1} (wording TODO)`} options={[[0,"No"],[1,"Yes"]]} value={choice(field, answers.assets[field])} onChange={(value) => setAsset(field, value)} help="Cleaned-file codes: 0 = No, 1 = Yes."/>)}</CardContent></Card>
    <Card><CardHeader><CardTitle className="text-base">Food-insecurity questions</CardTitle><p className="text-sm text-muted-foreground">Eight items cover food experiences in the last 12 months. Exact question text is TODO pending the questionnaire source. Codes: 1 = Yes, 2 = No, 3 = Don't know, 4 = Refused.</p></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2">{answers.food_answers.map((value, index) => <InputCodeField key={index} title={`Food item ${index + 1} (question wording TODO)`} options={[[1,"Yes"],[2,"No"],[3,"Don't know"],[4,"Refused"]]} value={value == null ? "" : String(value)} onChange={(selected) => setAnswers((prior) => ({ ...prior, food_answers: prior.food_answers.map((answer, i) => i === index ? selected === "" ? null : Number(selected) : answer) }))}/>)}</CardContent></Card>
    {preview && <Card><CardHeader><CardTitle className="text-base">Live derived preview</CardTitle><p className="text-sm text-muted-foreground">Computed by the backend from the current answers. This is not saved. For each vulnerability-oriented domain, 0 means the lowest modelled vulnerability signal and 1 the highest. Unknown means there was not enough observed input; it is not zero.</p></CardHeader><CardContent className="space-y-3"><div className="grid gap-3 sm:grid-cols-3"><Metric title="Persons per bedroom" value={preview.preview.persons_per_bedroom == null ? "Unknown" : Number(preview.preview.persons_per_bedroom).toFixed(3)} help="Roster count divided by bedrooms; not computed when evidence is insufficient."/><Metric title="Dependency ratio" value={preview.preview.dependency_ratio == null ? "Unknown" : Number(preview.preview.dependency_ratio).toFixed(3)} help="Under 15 and age 65+ relative to ages 15 to 64."/><Metric title="Food score" value={preview.preview.food_insecurity_score == null ? "Unknown" : `${preview.preview.food_insecurity_score} of 8`} help="Computed only when all eight answers are valid Yes or No responses."/></div><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(preview.domains).map(([key, value]) => { const leaf = leaves.find(([id]) => id === key); return <div className="rounded-md border p-2 text-sm" key={key}><p className="font-medium">{leaf?.[1] || key}</p><p>{value.degree == null ? "Degree: Unknown" : `Degree: ${Number(value.degree).toFixed(3)}`}</p><p className="text-xs text-muted-foreground">{leaf?.[2] || "No additional interpretation is documented."}</p><p className="text-muted-foreground">Evidence: {value.n_used} of {value.n_total} inputs</p></div> })}</div><p className="text-xs text-muted-foreground">{preview.preview.notes.join(" ")}</p></CardContent></Card>}
    <ErrorNotice error={error}/><Button type="submit" disabled={busy || Boolean(ageError)}>{busy ? "Calculatingâ€¦" : "Calculate temporary estimate"}</Button>
    {result && <WhatIfResult result={result}/>}
  </form>
}

function InputField({ title, help, children }) { return <label className="block space-y-1 text-sm"><span className="font-medium">{title}</span>{children}{help && <span className="block text-xs text-muted-foreground">{help}</span>}</label> }
function NumberInput({ title, value, min, step, onChange, help, status }) { return <InputField title={title} help={help}><input type="number" min={min} step={step} value={value ?? ""} onChange={(event) => onChange(event.target.value)} className="h-9 w-full rounded-md border bg-background px-3"/><select aria-label={`${title} answer status`} className="mt-1 h-8 w-full rounded-md border bg-background px-2 text-xs" value={status || (value == null ? "not_answered" : "answered")} onChange={(event) => onChange(event.target.value === "dont_know" ? "__dk" : event.target.value === "refused" ? "__refused" : "")}><option value="not_answered">Not answered</option><option value="dont_know">Don't know</option><option value="refused">Refused</option><option value="answered" disabled>Answered</option></select></InputField> }
function InputCodeField({ title, options, value, onChange, help }) { return <InputField title={title} help={help}><select aria-label={title} value={value} onChange={(event) => onChange(event.target.value)} className="h-9 w-full rounded-md border bg-background px-3"><option value="">Not answered</option><option value="__dk">Don't know</option><option value="__refused">Refused</option>{(options || []).map(([code, label]) => <option key={code} value={String(code)}>{label}</option>)}</select></InputField> }

function WhatIfResult({ result }) {
  const states = result.node_posteriors?.vulnerability || {}
  const highChance = Number(result.bn_p_high)
  const percentile = Number(result.comparison_percentile)
  return <Card><CardHeader><CardTitle>What-if result</CardTitle><p className="text-sm text-muted-foreground">Temporary model estimate for the values entered. Saved household rankings are unchanged, and this is not an eligibility decision.</p></CardHeader><CardContent className="space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Metric title="Expected vulnerability" value={Number(result.expected_vulnerability).toFixed(3)} help="Model summary from 0 (lower modeled vulnerability) to 1 (higher modeled vulnerability). Compare with the probability breakdown and input coverage." />
      <Metric title="Chance of high vulnerability" value={percent(highChance)} help="The model's estimated probability that the candidate is in its high-vulnerability state." />
      <Metric title="Comparison percentile" value={percentile.toFixed(1)} help="Position compared with saved baseline household scores. A higher percentile means a higher expected vulnerability score than more of the baseline records." />
      <Metric title="Evidence used" value={`${result.evidence_n_used ?? "Unavailable"} of ${result.evidence_n_total ?? "Unavailable"}`} help="Available inputs supporting this estimate; unknown answers are not treated as No or zero." />
    </div>
    <p className="text-sm">Comparison group: {result.comparison_group || "Unavailable"} ({Number(result.baseline_household_count || 0).toLocaleString()} saved records).</p>
    <section className="space-y-2"><h4 className="text-sm font-semibold">Estimated vulnerability level</h4><div className="grid gap-2 sm:grid-cols-3">{[["Lower", states.low], ["Middle", states.medium], ["Higher", states.high]].map(([name, value]) => <div key={name} className="rounded-lg border p-3"><p className="text-sm text-muted-foreground">{name} vulnerability</p><p className="text-lg font-semibold">{percent(value)}</p></div>)}</div><p className="text-sm text-muted-foreground">These three percentages show how the model distributes its estimate across the lower, middle, and higher vulnerability states. They add to about 100% (rounding may affect the total).</p></section>
    <section className="rounded-lg bg-muted/50 p-3 text-sm"><h4 className="font-semibold">Interpretation</h4><p className="mt-1">The model estimates a {percent(highChance)} chance of the high-vulnerability state. The expected vulnerability score is {Number(result.expected_vulnerability).toFixed(3)} on a 0 to 1 scale, and the candidate's comparison percentile is {percentile.toFixed(1)}. A higher percentile means the score is higher than more of the saved baseline household scores. Read these together with the entered domains and coverage: incomplete information can make the estimate less certain. These results support research comparison only; they do not determine eligibility or assistance.</p></section>
  </CardContent></Card>
}

export function BulkScoringPage({ embedded = false } = {}) {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [offset, setOffset] = useState(0)
  const [preview, setPreview] = useState(null)
  const [validation, setValidation] = useState(null)
  const downloadTemplate = () => { const a = document.createElement("a"); a.href = `${API_URL}/whatif/template.csv`; a.download = "component1_whatif_template.csv"; a.click() }
  const inspectFile = async selected => {
    setFile(selected); setPreview(null); setValidation(null); setResult(null); setRows(null)
    if (!selected) return
    const text = await selected.text()
    const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean)
    const header = lines[0]?.split(",").map(value => value.trim()) || []
    const required = leaves.flatMap(([key]) => [`${key}_degree`, `${key}_coverage_fraction`]).sort()
    const actual = [...header].sort()
    const errors = []
    if (new Set(header).size !== header.length) errors.push("The CSV has duplicate column names.")
    if (actual.join("\u0000") !== required.join("\u0000")) errors.push("Columns must exactly match the downloadable domain-score template.")
    const sampled = lines.slice(1, 6).map((line, index) => ({ row: index + 2, cells: line.split(",").length }))
    if (sampled.some(row => row.cells !== header.length)) errors.push("One or more preview rows have a different number of cells than the header.")
    setValidation(errors)
    setPreview({ rows: Math.max(0, lines.length - 1), columns: header, sampled })
  }
  const upload = async event => {
    event.preventDefault(); if (!file) return
    setBusy(true); setError(null); setResult(null); setRows(null)
    try {
      const response = await fetch(`${API_URL}/whatif`, { method: "POST", headers: { "Content-Type": "text/csv" }, body: file })
      const body = await response.json()
      if (!response.ok) throw new Error(body.error || body.detail || `Upload failed (${response.status})`)
      setResult(body); setOffset(0)
      const batchResponse = await fetch(`${API_URL}${body.results_url}`)
      const batch = await batchResponse.json()
      if (!batchResponse.ok) throw new Error(batch.error || "Unable to retrieve scored rows")
      setRows(batch)
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const loadPage = async nextOffset => {
    if (!result?.batch_id) return
    try { const response = await fetch(`${API_URL}/whatif/batches/${result.batch_id}?offset=${nextOffset}&limit=50`); const body = await response.json(); if (!response.ok) throw new Error(body.error || "Unable to load batch results"); setRows(body); setOffset(nextOffset) }
    catch (e) { setError(e) }
  }
  return <div className="space-y-5">
    {!embedded && <PageHeader title="Bulk CSV Scoring" description="Upload a CSV of candidate domain degrees. Files are scored in memory and are not saved to the database or disk." />}
    <ResearchNotice />
    <Card><CardHeader><CardTitle>Upload candidate file</CardTitle><p className="text-sm text-muted-foreground">Use the template columns exactly. Blank degree cells stay unobserved. This batch endpoint accepts domain degrees and coverage fractions, not raw questionnaire answers; raw questionnaire wording and a full raw-answer CSV schema remain open work.</p></CardHeader><CardContent><form onSubmit={upload} className="flex flex-wrap items-center gap-3"><Button type="button" variant="outline" onClick={downloadTemplate}>Download CSV template</Button><input type="file" accept=".csv,text/csv" onChange={e => inspectFile(e.target.files?.[0] || null)} aria-label="Choose candidate CSV"/><Button type="submit" disabled={!file || busy || Boolean(validation?.length) || !preview}>{busy ? "Uploadingâ€¦" : "Upload and score"}</Button></form>{preview && <div className="mt-4 space-y-2 text-sm" role="status"><p>Preview: {preview.rows} candidate rows; expected {preview.columns.length} domain input columns.</p>{validation?.length ? <ul className="list-disc pl-5 text-destructive">{validation.map(item => <li key={item}>{item}</li>)}</ul> : <p>Header and first {preview.sampled.length} row shapes look valid. Full value validation happens before any row is scored.</p>}</div>}</CardContent></Card>
    <ErrorNotice error={error} />
    {result && <Card><CardContent className="space-y-2 p-5"><p>Scored {result.scored_rows} of {result.submitted_rows} rows; rejected {result.rejected_rows}.</p><p className="break-all text-xs text-muted-foreground">Batch: {result.batch_id} Â· results expire after a short session period.</p>{result.errors?.length > 0 && <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">{JSON.stringify(result.errors, null, 2)}</pre>}</CardContent></Card>}
    {rows && <><div className="rounded-xl border"><Table><TableHeader><TableRow>{["Candidate row", "Expected vulnerability", "P(high)", "Comparison percentile", "Uncertainty"].map(x => <TableHead key={x}>{x}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.items.map(row => <TableRow key={row.candidate_row_id}>{[row.candidate_row_id, row.expected_vulnerability, row.bn_p_high, row.comparison_percentile, row.uncertainty_entropy].map((v,i) => <TableCell key={i}>{typeof v === "number" ? v.toFixed(3) : v}</TableCell>)}</TableRow>)}</TableBody></Table></div><div className="flex gap-2"><Button variant="outline" disabled={offset === 0} onClick={() => loadPage(Math.max(0, offset - 50))}>Previous</Button><Button variant="outline" disabled={offset + 50 >= rows.total} onClick={() => loadPage(offset + 50)}>Next</Button></div></>}
  </div>
}

export function SummaryPage() {
  const [data, setData] = useState(null); const [error, setError] = useState(null)
  useEffect(() => { Promise.all([api("/summary"), api("/model-info"), api("/health")]).then(([summary, model, health]) => setData({ summary, model, health })).catch(setError) }, [])
  return <div className="space-y-5"><PageHeader title="Summary & Model Info" description="Current API health, scored dataset summary, and baseline model configuration."/><ResearchNotice/><ErrorNotice error={error}/>{data && <div className="grid gap-4 md:grid-cols-2"><Card><CardHeader><CardTitle>Service status</CardTitle></CardHeader><CardContent><p>{data.health.status} Â· {data.health.data_mode || "data mode unavailable"}</p><p className="text-sm text-muted-foreground">Loaded rows: {data.health.loaded_rows ?? data.model.household_count}</p></CardContent></Card><Card><CardHeader><CardTitle>Baseline model</CardTitle></CardHeader><CardContent><p>{data.model.baseline_config}</p><p className="text-sm text-muted-foreground">Version {data.model.pipeline_version} Â· {data.model.baseline_leaves?.length} domains</p><p className="mt-2 text-sm">Exposure in baseline: {String(data.model.exposure_in_baseline)}</p></CardContent></Card><Card className="md:col-span-2"><CardHeader><CardTitle>Score summary</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-3"><p>Households: {data.summary.household_count}</p><p>Mean P(high): {Number(data.summary.score_summary.mean_bn_p_high).toFixed(3)}</p><p>Mean uncertainty: {Number(data.summary.score_summary.mean_uncertainty_entropy).toFixed(3)}</p>{Object.entries(data.summary.score_summary.expected_vulnerability_quantiles).map(([q,v]) => <p key={q}>Expected vulnerability q{Number(q)*100}: {Number(v).toFixed(3)}</p>)}</CardContent></Card><p className="md:col-span-2 text-xs text-muted-foreground">{data.model.use_notice}</p></div>}</div>
}

export function SensitivityPage() {
  const [data, setData] = useState(null); const [error, setError] = useState(null)
  useEffect(() => { beneficiaryApi.sensitivity().then(setData).catch(setError) }, [])
  return <div className="space-y-5"><PageHeader title="Robustness & Decisions" description="See how saved alternatives affect rank order and model outputs."/><ResearchNotice/><ErrorNotice error={error}/>{data && <><Card><CardHeader><CardTitle>Saved sensitivity scenarios</CardTitle><p className="text-sm text-muted-foreground">These are precomputed comparisons against the primary run. They are not confidence intervals and do not rerun the model.</p></CardHeader><CardContent><div className="overflow-x-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead>Scenario</TableHead><TableHead>Status</TableHead><TableHead><span className="inline-flex items-center gap-1">Rank correlation<GlossaryEntry id="rank_correlation"/></span></TableHead><TableHead>Mean change in P(high)</TableHead><TableHead>Changing most-probable level</TableHead><TableHead>Records compared</TableHead></TableRow></TableHeader><TableBody>{(data.scenarios || []).map((scenario) => <TableRow key={scenario.scenario}><TableCell className="font-medium">{scenario.scenario.replaceAll("_", " ")}</TableCell><TableCell>{scenario.status}</TableCell><TableCell>{scenario.spearman_expected_vulnerability_vs_baseline == null ? "Unavailable" : Number(scenario.spearman_expected_vulnerability_vs_baseline).toFixed(3)}</TableCell><TableCell>{scenario.mean_absolute_bn_p_high_change == null ? "Unavailable" : `${(Number(scenario.mean_absolute_bn_p_high_change) * 100).toFixed(2)} percentage points`}</TableCell><TableCell>{scenario.most_probable_vulnerability_level_changed_share == null ? "Unavailable" : `${(Number(scenario.most_probable_vulnerability_level_changed_share) * 100).toFixed(1)}% (${scenario.most_probable_vulnerability_level_changed_n} records)`}</TableCell><TableCell>{scenario.rank_correlation_n ?? scenario.p_high_comparison_n ?? "Unavailable"}</TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card><DecisionLog/></>}</div>
}

function DecisionLog() {
  const [data, setData] = useState(null); const [error, setError] = useState(null)
  useEffect(() => { beneficiaryApi.spec().then(setData).catch(setError) }, [])
  return <Card><CardHeader><CardTitle>Decision log & approved IDs</CardTitle></CardHeader><CardContent className="space-y-3"><ErrorNotice error={error}/>{data && <><p className="text-sm">Decision records: {data.approved_decisions?.length ?? 0}</p><pre className="max-h-96 overflow-auto rounded-md bg-muted p-4 text-xs">{JSON.stringify(data.approved_decisions, null, 2)}</pre><details><summary className="cursor-pointer text-sm font-medium">View source decision documents</summary>{data.documents?.map(doc => <details className="mt-2" key={doc.filename}><summary className="cursor-pointer text-sm">{doc.filename}</summary><pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-xs">{doc.content}</pre></details>)}</details></>}</CardContent></Card>
}



