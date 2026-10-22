import { useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { beneficiaryApi } from "../api"
import { GlossaryEntry } from "../components/ResearchPageFrame"

const pct = (value) => value == null ? "Unavailable" : `${(Number(value) * 100).toFixed(1)}%`

export function OverviewPage() {
  const [summary, setSummary] = useState(null)
  const [geography, setGeography] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([beneficiaryApi.summary(), beneficiaryApi.geography()])
      .then(([summaryBody, geographyBody]) => { setSummary(summaryBody); setGeography(geographyBody) })
      .catch(setError)
  }, [])

  const provinceNames = Object.fromEntries((geography?.provinces || []).map((item) => [String(item.code), item.name]))
  const districtNames = Object.fromEntries((geography?.districts || []).map((item) => [String(item.code), item.name]))
  const provinces = summary?.geography?.by_province || []
  const districts = summary?.geography?.by_district || []
  const bins = summary?.expected_vulnerability_histogram || []
  const maxCount = Math.max(...bins.map((bin) => bin.households_n), 1)
  const coverage = summary?.coverage_by_input || []

  return <div className="space-y-5">
    <PageHeader title="Overview" description="Explore the saved research scores, their distribution, and how much model input evidence is available." />
    {error && <p role="alert" className="rounded-md border p-3 text-sm">{error.message || String(error)}</p>}
    {!summary && !error && <p role="status" className="text-sm text-muted-foreground">Loading overview…</p>}
    {summary && <>
      <Card><CardHeader><CardTitle>Saved score distribution</CardTitle><p className="text-sm text-muted-foreground">Comparison group: all {Number(summary.household_count).toLocaleString()} saved baseline household records. Counts are unweighted sample counts.</p></CardHeader><CardContent>
        <div className="mb-3 flex flex-wrap gap-4 text-sm"><span>Median vulnerability level: <strong>{Number(summary.median_expected_vulnerability).toFixed(3)}</strong></span><span>Evidence availability: <strong>{coverage.length ? `${coverage.length} model inputs summarized` : "Unavailable in this data mode"}</strong></span><GlossaryEntry id="vulnerability_level" /><GlossaryEntry id="evidence_used" /></div>
        {bins.length ? <div className="overflow-x-auto"><svg viewBox="0 0 900 280" role="img" aria-label={`Histogram of expected vulnerability levels for ${Number(summary.household_count).toLocaleString()} saved household records`} className="min-w-[620px] w-full">
          <line x1="55" y1="230" x2="865" y2="230" stroke="currentColor" strokeOpacity=".35" />
          {bins.map((bin, index) => { const width = 810 / bins.length; const height = (bin.households_n / maxCount) * 178; return <g key={`${bin.score_min}-${index}`}><rect x={55 + index * width + 3} y={230 - height} width={Math.max(width - 6, 2)} height={height} rx="3" fill="hsl(var(--muted-foreground))" fillOpacity=".58"><title>{bin.households_n.toLocaleString()} records; score {bin.score_min.toFixed(3)} to {bin.score_max.toFixed(3)}</title></rect><text x={55 + index * width + width / 2} y="249" textAnchor="middle" fontSize="10" fill="currentColor">{bin.score_min.toFixed(2)}</text></g> })}
          {summary.median_expected_vulnerability != null && <g><line x1={55 + ((summary.median_expected_vulnerability - bins[0].score_min) / Math.max(bins[bins.length - 1].score_max - bins[0].score_min, 1e-9)) * 810} y1="32" x2={55 + ((summary.median_expected_vulnerability - bins[0].score_min) / Math.max(bins[bins.length - 1].score_max - bins[0].score_min, 1e-9)) * 810} y2="232" stroke="currentColor" strokeDasharray="6 4" strokeWidth="2"><title>Median: {Number(summary.median_expected_vulnerability).toFixed(3)}</title></line><text x={55 + ((summary.median_expected_vulnerability - bins[0].score_min) / Math.max(bins[bins.length - 1].score_max - bins[0].score_min, 1e-9)) * 810} y="25" textAnchor="middle" fontSize="12" fill="currentColor">Median</text></g>}
          <text x="460" y="275" textAnchor="middle" fontSize="12" fill="currentColor">Expected vulnerability level (0 to 1)</text>
          <text x="14" y="132" textAnchor="middle" fontSize="12" fill="currentColor" transform="rotate(-90 14 132)">Saved household count</text>
        </svg><p className="text-xs text-muted-foreground">Bars show the observed score distribution; the dashed line marks the median. This distribution is not a percentile chart.</p></div> : <p className="text-sm text-muted-foreground">Score distribution is unavailable.</p>}
      </CardContent></Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Household counts by province</CardTitle><p className="text-sm text-muted-foreground">Unweighted sample counts from the saved dataset. Means are descriptive summaries.</p></CardHeader><CardContent><div className="rounded-lg border"><Table><TableHeader><TableRow><TableHead>Province</TableHead><TableHead>Sample count</TableHead><TableHead>Mean expected level</TableHead></TableRow></TableHeader><TableBody>{provinces.map((row) => <TableRow key={row.a_01_province}><TableCell>{provinceNames[String(row.a_01_province)] || "Unknown code"}</TableCell><TableCell>{Number(row.households_n).toLocaleString()}</TableCell><TableCell>{Number(row.mean_bn_expected_vulnerability).toFixed(3)}</TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card>
        <Card><CardHeader><CardTitle>Household counts by district</CardTitle><p className="text-sm text-muted-foreground">Unweighted sample counts. District averages are hidden for groups below 10 records.</p></CardHeader><CardContent><div className="max-h-80 overflow-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead>Province</TableHead><TableHead>District</TableHead><TableHead>Sample count</TableHead><TableHead>Mean expected level</TableHead></TableRow></TableHeader><TableBody>{districts.map((row) => <TableRow key={row.a_02_district}><TableCell>{provinceNames[String(row.a_01_province)] || "Unknown code"}</TableCell><TableCell>{districtNames[String(row.a_02_district)] || "Unknown code"}</TableCell><TableCell>{Number(row.households_n).toLocaleString()}</TableCell><TableCell>{Number(row.households_n) < 10 ? "Suppressed" : Number(row.mean_bn_expected_vulnerability).toFixed(3)}</TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card>
      </div>
      <Card><CardHeader><CardTitle>Evidence coverage by model input</CardTitle><p className="text-sm text-muted-foreground">Available and unknown input counts from the Stage 4 coverage data. These are model inputs, not a count of every survey response.</p></CardHeader><CardContent>{coverage.length ? <div className="rounded-lg border"><Table><TableHeader><TableRow><TableHead>Input</TableHead><TableHead>Available</TableHead><TableHead>Unknown</TableHead><TableHead>Known share</TableHead></TableRow></TableHeader><TableBody>{coverage.map((row) => <TableRow key={row.id}><TableCell>{row.label}</TableCell><TableCell>{Number(row.known_n).toLocaleString()}</TableCell><TableCell>{Number(row.unknown_n).toLocaleString()}</TableCell><TableCell>{pct(row.known_n / Math.max(row.total_n, 1))}</TableCell></TableRow>)}</TableBody></Table></div> : <p className="text-sm text-muted-foreground">Input-level coverage is not available for this data mode.</p>}</CardContent></Card>
      <div className="flex flex-wrap gap-2"><Button asChild><Link to="/beneficiary-selection/households">Explore household scores</Link></Button><Button asChild variant="outline"><Link to="/beneficiary-selection/assess">Assess a household</Link></Button></div>
    </>}
  </div>
}
