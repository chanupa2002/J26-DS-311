import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import {
  ChanceAfterChart,
  decimal,
  EvidenceTable,
  RecommendationEvidence,
  ShapGroupShare,
  SimulatedBadge,
  spreadText,
  TransitionTable,
  V2PageState,
} from "../components"
import { useV2Evidence } from "../hooks"

function RegisterTable({ rows }) {
  return (
    <Table className="min-w-[640px]">
      <TableHeader>
        <TableRow>
          <TableHead>Threshold</TableHead>
          <TableHead>Value</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Note</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.threshold}>
            <TableCell className="font-medium">{row.threshold}</TableCell>
            <TableCell>{row.value}</TableCell>
            <TableCell className="text-xs">
              <span className="block text-muted-foreground">{row.source_type}</span>
              {row.source}
            </TableCell>
            <TableCell className="text-xs">{row.note || "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function ModelEvidencePage() {
  const evidence = useV2Evidence()
  if (evidence.isPending || evidence.isError) {
    return <V2PageState loading={evidence.isPending} error={evidence.error} onRetry={() => evidence.refetch()} />
  }
  const data = evidence.data
  const register = data.threshold_register ?? []
  const alertRows = register.filter((row) => String(row.used_for).startsWith("high_alert"))
  const transitions = data.transitions
  const after = transitions?.p_high_after ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <SimulatedBadge isSynthetic={data.is_synthetic} />
        {data.note && <span className="text-muted-foreground">{data.note}</span>}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">In plain words</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {transitions?.text && <p>{transitions.text}</p>}
          <p>
            The 3-month model is only slightly better than simply assuming that risk stays the same as this month.
          </p>
          <p>
            The 6-month model is not better than that simple assumption, so its outlook is shown as indicative only and it
            never raises an alert.
          </p>
          <p>
            The outcome labels used for training and testing come from simulated households, so these results are not a
            real-world validation.
          </p>
        </CardContent>
      </Card>

      {transitions && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">How risk changes from one month to the next</CardTitle>
              <CardDescription>
                Out of 10 households in each risk class this month, how many were in each class at the next visit. Based on{" "}
                {transitions.n_transitions} month-to-month changes of simulated households. Not a prediction model.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 sm:px-6 sm:pb-6">
              <TransitionTable transitions={transitions} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Chance of High risk after 1–6 months</CardTitle>
              <CardDescription>One line for each risk class this month, using the month-to-month table.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ChanceAfterChart rows={after} />
              {after.length > 1 && (
                <p className="text-sm">
                  After 1 month the chance of High is {spreadText(after[0])}, depending on this month&apos;s risk. After{" "}
                  {after[after.length - 1].months} months it is {spreadText(after[after.length - 1])}: the lines come
                  together, so this month&apos;s risk tells us little about month {after[after.length - 1].months}. That is
                  why 6-month forecasts are rough and never raise an alert.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Model compared with &quot;risk stays the same&quot;</CardTitle>
          <CardDescription>Higher is better for both metrics. Persistence = predict this month&apos;s risk again.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:px-6 sm:pb-6">
          <EvidenceTable comparisons={data.comparisons} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Alert thresholds</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <ul className="space-y-1">
              {Object.entries(data.alert_thresholds).map(([horizon, value]) => (
                <li key={horizon}>
                  <span className="font-medium">{horizon}:</span>{" "}
                  {value === null ? "no alert (no reliable threshold)" : `alert when P(High) ≥ ${decimal(value)}`}
                </li>
              ))}
            </ul>
            {alertRows.map((row) => (
              <p key={row.threshold} className="text-xs text-muted-foreground">
                {row.threshold}: {row.value}. {row.source}
                {row.note ? ` (${row.note})` : ""}
              </p>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">What drives the 3-month model</CardTitle>
            <CardDescription>Share of all SHAP effects per factor group.</CardDescription>
          </CardHeader>
          <CardContent>
            <ShapGroupShare shares={data.shap_group_share} />
          </CardContent>
        </Card>
      </div>

      <RecommendationEvidence data={data.recommendations} />

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Limitations</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {data.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">All thresholds and their sources</CardTitle>
          <CardDescription>None of these values are typed in the app: they come from the threshold register.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:px-6 sm:pb-6">
          <RegisterTable rows={register} />
        </CardContent>
      </Card>
    </div>
  )
}
