import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getMonitoringRecords } from "../api"

function Flag({ flag, source }) {
  return <div className="rounded-lg border p-3"><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{flag.code}</p><p className="mt-1 text-sm text-muted-foreground">{flag.reason}</p></div><Badge variant={flag.severity === "critical" ? "destructive" : "outline"}>{source}</Badge></div></div>
}

function isInformationalUnknown(item) {
  const code = item.code || item.check_code || ""
  const reason = item.reason || ""
  return (/no previous|no same-category|no same-place|no cross-household/i.test(reason) || code === "WEB_IMAGE_MATCH" && /unavailable|not configured/i.test(reason))
}

function Metric({ label, explanation, value }) {
  return <div><span className="text-muted-foreground">{label} <span className="text-xs">({explanation})</span></span><p className="font-medium">{value}</p></div>
}

function Report({ record }) {
  const financialFlags = record.financial_report?.flags || []
  const imageFlags = record.image_report?.flagged_checks || []
  const unknowns = [...(record.financial_report?.unknowns || []), ...(record.image_report?.unknown_checks || [])]
  const reviewUnknowns = unknowns.filter((item) => !isInformationalUnknown(item))
  const informationalUnknowns = unknowns.filter(isInformationalUnknown)
  const total = financialFlags.length + imageFlags.length
  const hasPreviousRecord = record.financial_report?.has_previous_record === true
  return <Card><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle>{record.household_id || "Unknown household"}</CardTitle><CardDescription>{record.month || "No period"} · {record.livelihood_category || "Category unavailable"} · Visit {record.visit_id}</CardDescription></div><Badge variant={total ? "destructive" : "secondary"}>{total ? `${total} flag${total === 1 ? "" : "s"} raised` : "No flags"}</Badge></div></CardHeader><CardContent className="space-y-4">{total ? <div className="grid gap-3 lg:grid-cols-2">{financialFlags.map((flag, index) => <Flag key={`financial-${index}`} flag={flag} source="Financial" />)}{imageFlags.map((flag, index) => <Flag key={`image-${index}`} flag={{ ...flag, code: flag.check_code || flag.code }} source="Image" />)}</div> : <div className="flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 className="size-4" /> No raised flags in the available reports.</div>}{reviewUnknowns.length > 0 && <details className="rounded-lg border p-3 text-sm"><summary className="cursor-pointer font-medium">{reviewUnknowns.length} result(s) need officer review</summary><div className="mt-3 space-y-2 text-muted-foreground">{reviewUnknowns.map((item, index) => <p key={index}><span className="font-medium text-foreground">{item.code || item.check_code}:</span> {item.reason}</p>)}</div></details>}{informationalUnknowns.length > 0 && <details className="rounded-lg border p-3 text-sm text-muted-foreground"><summary className="cursor-pointer font-medium">{informationalUnknowns.length} informational result(s)</summary><div className="mt-3 space-y-2">{informationalUnknowns.map((item, index) => <p key={index}><span className="font-medium text-foreground">{item.code || item.check_code}:</span> {item.reason}</p>)}</div></details>}<div className="grid gap-3 text-sm sm:grid-cols-4">{hasPreviousRecord && <><Metric label="Financial level" explanation="risk category" value={record.financial_report?.level || "Unknown"} /><Metric label="Risk" explanation="model score" value={record.financial_report?.risk ?? "Unknown"} /><Metric label="Confidence" explanation="data quality" value={record.financial_report?.confidence ?? "Unknown"} /></>}<Metric label="Image summary" explanation="evidence checks" value={record.image_report?.summary || "Unavailable"} /></div>{!hasPreviousRecord && <p className="text-xs text-muted-foreground">Risk metrics will appear after a subsequent monitoring record is submitted for this household.</p>}</CardContent></Card>
}

export function DashboardPage() {
  const query = useQuery({ queryKey: ["evidence-trust-monitoring"], queryFn: getMonitoringRecords })
  const records = query.data || []
  return <div className="space-y-6"><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-2xl font-semibold tracking-tight">Officer dashboard</h1><p className="mt-1 text-sm text-muted-foreground">Review household-level fraud signals from financial and image analysis.</p></div><Button variant="outline" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw className={query.isFetching ? "size-4 animate-spin" : "size-4"} /> Refresh</Button></div>{query.isError && <Card><CardContent className="flex items-center gap-3 p-6 text-sm text-destructive"><AlertTriangle className="size-5" />{query.error.message}</CardContent></Card>}{!query.isError && !records.length && !query.isPending && <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No monitoring records have been submitted yet.</CardContent></Card>}{query.isPending && <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">Loading monitoring reports…</CardContent></Card>}<div className="space-y-4">{records.map((record) => <Report key={record.visit_id} record={record} />)}</div></div>
}
