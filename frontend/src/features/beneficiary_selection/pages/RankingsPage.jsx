import { useEffect, useState } from "react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { beneficiaryApi } from "../api"

const METHODS = [
  ["F1", "Fuzzy + Bayesian framework", "Current v0.2 interim model."],
  ["F0", "Fuzzy baseline", "Fuzzy domain score without the Bayesian network."],
  ["B1", "Bayesian, all available memberships", "Bayesian network using the available fuzzy inputs."],
  ["B2", "PCA baseline", "Principal component score, calculated for complete cases."],
  ["B3", "Threshold counting baseline", "Counts observed indicators above the documented threshold."],
]
const LABEL = "Research output - not an eligibility determination"
const number = (value, digits = 3) => value == null ? "Unavailable" : Number(value).toFixed(digits)

export function RankingsPage() {
  const [method, setMethod] = useState("F1")
  const [page, setPage] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError("")
    beneficiaryApi.stage6Rankings({ method, offset: page * 50, limit: 50 })
      .then((result) => { if (active) setData(result) })
      .catch((reason) => { if (active) setError(reason?.message || "Rankings could not be loaded.") })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [method, page])

  const selected = METHODS.find(([key]) => key === method)
  const items = data?.items || []
  const pageCount = data ? Math.ceil(data.total / 50) : 0

  return <div className="space-y-5">
    <PageHeader title="Stage 6 Rankings" description="Compare the household ordering from the interim model and four transparent baselines." />
    <Card>
      <CardHeader><CardTitle>Choose a ranking method</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <label className="grid max-w-xl gap-1 text-sm font-medium" htmlFor="ranking-method">Method
          <select id="ranking-method" className="h-10 rounded-md border bg-background px-3" value={method} onChange={(event) => { setMethod(event.target.value); setPage(0) }}>
            {METHODS.map(([key, title]) => <option key={key} value={key}>{key} · {title}</option>)}
          </select>
        </label>
        <p className="text-sm text-muted-foreground">{selected?.[2]}</p>
        <p className="rounded-md bg-muted/50 p-3 text-sm"><strong>How to read this:</strong> Rank 1 has the highest score within the selected method. The score is a relative research estimate; it does not establish eligibility or a verified need. Evidence counts show how many inputs were available for that method.</p>
        {method === "F1" && <p className="text-sm text-muted-foreground">Rank interval columns show the 5th, median, and 95th percentile rank across the Stage 6 perturbation runs. Wider intervals mean the rank moved more under those perturbations.</p>}
        <p className="text-xs text-muted-foreground">{LABEL}</p>
      </CardContent>
    </Card>
    <Card>
      <CardHeader><CardTitle>Household ordering</CardTitle><p className="text-sm text-muted-foreground">{data ? `${Number(data.total).toLocaleString()} aligned research records` : "Ranking results"} · page {page + 1}{pageCount ? ` of ${pageCount}` : ""}</p></CardHeader>
      <CardContent>
        {error && <div role="alert" className="mb-4 rounded-md border border-destructive/50 p-3 text-sm">{error} If running locally, generate the Stage 6 outputs and restart the API.</div>}
        {loading && <p className="py-6 text-sm text-muted-foreground" role="status">Loading rankings…</p>}
        {!loading && !error && <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Rank</TableHead><TableHead>Research row</TableHead><TableHead>Province code</TableHead><TableHead>District code</TableHead><TableHead>Score</TableHead><TableHead>Evidence used</TableHead>{method === "F1" && <><TableHead>Rank p05</TableHead><TableHead>Median</TableHead><TableHead>Rank p95</TableHead></>}</TableRow></TableHeader>
            <TableBody>{items.map((item) => <TableRow key={`${method}-${item.row_id}`}>
              <TableCell className="font-semibold">{Number(item.rank_position).toLocaleString()}</TableCell><TableCell>{item.row_id}</TableCell><TableCell>{item.province}</TableCell><TableCell>{item.district}</TableCell><TableCell>{number(item.score)}</TableCell><TableCell>{item.evidence_n_used ?? "Unavailable"}</TableCell>
              {method === "F1" && <><TableCell>{number(item.rank_p05, 1)}</TableCell><TableCell>{number(item.rank_p50, 1)}</TableCell><TableCell>{number(item.rank_p95, 1)}</TableCell></>}
            </TableRow>)}</TableBody>
          </Table>
          {!items.length && <p className="py-6 text-sm text-muted-foreground">No ranking rows are available.</p>}
        </div>}
        <div className="mt-4 flex items-center justify-between gap-3">
          <Button variant="outline" disabled={page === 0 || loading} onClick={() => setPage((current) => Math.max(0, current - 1))}>Previous</Button>
          <span className="text-sm text-muted-foreground">Showing {data && items.length ? `${page * 50 + 1}–${page * 50 + items.length} of ${Number(data.total).toLocaleString()}` : "—"}</span>
          <Button variant="outline" disabled={!data || page + 1 >= pageCount || loading} onClick={() => setPage((current) => current + 1)}>Next</Button>
        </div>
      </CardContent>
    </Card>
  </div>
}
