import { Info } from "lucide-react"

import { WeakSignalTag } from "@/components/explain/WeakSignalTag"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { METRICS } from "../constants"
import { formatDateTime, formatMetric, trainingDataLabel } from "../utils"
import { StatusBadge } from "./StatusBadge"

function Detail({ label, children }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

export function ModelMetricsCard({ model }) {
  const metrics = model.test_metrics || {}
  const period = model.training_period || {}
  const notEmbargoed = /no embargo/i.test(model.validation_methodology || "")

  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{model.horizon} model</CardTitle>
          <div className="flex items-center gap-2">
            <WeakSignalTag show={notEmbargoed} />
            <StatusBadge status={model.model_status} />
          </div>
        </div>
        <CardDescription>
          {model.model_name} · {model.algorithm} · risk class{" "}
          {model.horizon_months} months ahead
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Test metric (one test month)</TableHead>
              <TableHead className="text-right">Model</TableHead>
              <TableHead className="text-right">Persistence baseline</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {METRICS.map(([key, label]) => (
              <TableRow key={key}>
                <TableCell>{label}</TableCell>
                <TableCell className="text-right font-medium tabular-nums">
                  {formatMetric(metrics[key])}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {key === "Macro_F1"
                    ? formatMetric(model.persistence_baseline_test_macro_f1)
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <dl className="grid gap-3 sm:grid-cols-2">
          <Detail label="Training data">
            {trainingDataLabel(model.data_basis)}
          </Detail>
          <Detail label="Created">{formatDateTime(model.created)}</Detail>
          <Detail label="Prediction months">
            {period.prediction_months || "—"}
          </Detail>
          <Detail label="Target months">{period.target_months || "—"}</Detail>
        </dl>

        {model.validation_methodology && (
          <Tooltip>
            <TooltipTrigger className="flex items-center gap-1 text-left text-sm text-muted-foreground underline decoration-dotted underline-offset-4">
              <Info className="size-4 shrink-0" />
              How it was tested
            </TooltipTrigger>
            <TooltipContent className="max-w-sm">
              {model.validation_methodology}
            </TooltipContent>
          </Tooltip>
        )}
      </CardContent>
    </Card>
  )
}
