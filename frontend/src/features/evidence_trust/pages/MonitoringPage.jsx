import { useMemo, useRef, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { CheckCircle2, FileImage, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { submitMonitoring } from "../api"
import { initialForm, LIVELIHOOD_CATEGORIES, PROBLEMS } from "../constants"

const YEARS = Array.from({ length: 11 }, (_, index) => String(new Date().getFullYear() - index))
const MONTHS = Array.from({ length: 12 }, (_, index) => ({ value: String(index + 1), label: new Date(2024, index).toLocaleString("en", { month: "long" }) }))

function Field({ label, children, hint }) {
  return <label className="space-y-2 text-sm font-medium"><span>{label}</span>{children}{hint && <span className="block text-xs font-normal text-muted-foreground">{hint}</span>}</label>
}

function SelectField({ value, onChange, children, required = false }) {
  return <select required={required} value={value} onChange={onChange} className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus:outline-none focus:ring-2 focus:ring-ring"><option value="">Select…</option>{children}</select>
}

function BooleanSelect({ value, onChange }) {
  return <SelectField value={value} onChange={onChange}><option value="true">Yes</option><option value="false">No</option></SelectField>
}

export function MonitoringPage() {
  const [form, setForm] = useState(initialForm)
  const [problems, setProblems] = useState(() => Object.fromEntries(PROBLEMS.map(([key]) => [key, false])))
  const [image, setImage] = useState(null)
  const [bills, setBills] = useState([])
  const imageInput = useRef(null)
  const billInput = useRef(null)
  const problemCount = useMemo(() => Object.values(problems).filter(Boolean).length, [problems])
  const mutation = useMutation({
    mutationFn: () => submitMonitoring({ ...form, problem_count: problemCount, image, bills }),
    onSuccess: () => {
      setForm(initialForm)
      setProblems(Object.fromEntries(PROBLEMS.map(([key]) => [key, false])))
      setImage(null)
      setBills([])
      if (imageInput.current) imageInput.current.value = ""
      if (billInput.current) billInput.current.value = ""
    },
  })

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const handleSubmit = (event) => {
    event.preventDefault()
    mutation.mutate()
  }

  return <div className="space-y-6">
    <div><h1 className="text-2xl font-semibold tracking-tight">Monitoring form</h1><p className="mt-1 text-sm text-muted-foreground">Capture the household visit, livelihood evidence, and financial signals for review.</p></div>
    {mutation.isSuccess && <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><CheckCircle2 className="size-5" /> Record submitted and both analyses completed.</div>}
    {mutation.isError && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{mutation.error.message}</div>}
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card><CardHeader><CardTitle>Visit details</CardTitle><CardDescription>Identify the household and select the period used by both analysis modules.</CardDescription></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Household number"><Input required value={form.household_id} onChange={update("household_id")} placeholder="HH-000123" /></Field>
        <Field label="Year"><SelectField required value={form.year} onChange={update("year")}>{YEARS.map((year) => <option key={year} value={year}>{year}</option>)}</SelectField></Field>
        <Field label="Month"><SelectField required value={form.month_number} onChange={update("month_number")}>{MONTHS.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}</SelectField></Field>
        <Field label="Livelihood category"><SelectField required value={form.livelihood_category} onChange={update("livelihood_category")}>{LIVELIHOOD_CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}</SelectField></Field>
      </CardContent></Card>

      <Card><CardHeader><CardTitle>Financial and livelihood inputs</CardTitle><CardDescription>These fields map to the financial-risk model's Visit contract.</CardDescription></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Total grant amount (first record only)" hint="Enter this for a new household. Leave blank for later records; the saved amount will be reused."><Input type="number" min="0" step="0.01" value={form.grant_amount_lkr} onChange={update("grant_amount_lkr")} /></Field>
        <Field label="Monthly expenditure (LKR)"><Input required type="number" min="0" step="0.01" value={form.monthly_expenditure_lkr} onChange={update("monthly_expenditure_lkr")} /></Field>
        <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">Grant spent and grant remaining are calculated by the backend from the household grant amount and cumulative monthly expenditure.</div>
        <Field label="Grant use status"><SelectField value={form.grant_use_status} onChange={update("grant_use_status")}><option>Received, fully used, bills settled</option><option>Received, fully used, bills not settled</option><option>Received, not fully used</option><option>Not received</option></SelectField></Field>
        <Field label="Used according to plan"><BooleanSelect value={form.grant_used_per_plan} onChange={update("grant_used_per_plan")} /></Field>
        <Field label="Business currently running"><BooleanSelect value={form.business_running} onChange={update("business_running")} /></Field>
        <Field label="Profit reported"><BooleanSelect value={form.profit} onChange={update("profit")} /></Field>
        <Field label="Borrowed money"><BooleanSelect value={form.borrowed_money} onChange={update("borrowed_money")} /></Field>
        <Field label="Revenue this period (LKR)"><Input type="number" min="0" step="0.01" value={form.revenue_mid_lkr} onChange={update("revenue_mid_lkr")} /></Field>
        <Field label="Saved amount (LKR)"><Input type="number" min="0" step="0.01" value={form.saved_amount_lkr} onChange={update("saved_amount_lkr")} /></Field>
        <Field label="Record keeping level" hint="Select the household's usual record-keeping frequency."><SelectField required value={form.record_keeping_level} onChange={update("record_keeping_level")}><option value="0">0 — Keeps no written records</option><option value="1">1 — A few times a month</option><option value="2">2 — Once or twice a week</option><option value="3">3 — Daily</option></SelectField></Field>
        <Field label="Disaster impact reported"><BooleanSelect value={form.disaster_impact_reported} onChange={update("disaster_impact_reported")} /></Field>
        <Field label="Livelihood difficulty reported"><BooleanSelect value={form.livelihood_difficulty_reported} onChange={update("livelihood_difficulty_reported")} /></Field>
      </CardContent></Card>

      <Card><CardHeader><CardTitle>Problems observed</CardTitle><CardDescription>Select every problem that is true. The checked total is sent as problem_count.</CardDescription></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{PROBLEMS.map(([key, label]) => <label key={key} className="flex items-center gap-3 rounded-lg border p-3 text-sm"><input type="checkbox" checked={problems[key]} onChange={(event) => setProblems((current) => ({ ...current, [key]: event.target.checked }))} className="size-4 accent-primary" />{label}</label>)}<div className="sm:col-span-2 lg:col-span-3 text-sm text-muted-foreground">Problem count: <span className="font-semibold text-foreground">{problemCount}</span></div></CardContent></Card>

      <Card><CardHeader><CardTitle>Evidence uploads</CardTitle><CardDescription>Upload one livelihood image and any bills for the selected monitoring period.</CardDescription></CardHeader><CardContent className="grid gap-5 sm:grid-cols-2">
        <Field label="Livelihood evidence image"><Input ref={imageInput} required type="file" accept="image/*" onChange={(event) => setImage(event.target.files?.[0] || null)} /><span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><FileImage className="size-4" />{image?.name || "One image is required"}</span></Field>
        <Field label="Bill images" hint="You may select multiple files."><Input ref={billInput} type="file" accept="image/*" multiple onChange={(event) => setBills(Array.from(event.target.files || []))} /><span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><Upload className="size-4" />{bills.length ? `${bills.length} bill file(s) selected` : "No bills selected"}</span></Field>
      </CardContent></Card>
      <div className="flex justify-end"><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Running analysis…" : "Submit for fraud analysis"}</Button></div>
    </form>
  </div>
}
