import { ChevronDown } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { ABOUT_DATA, BASELINE_SIMILAR_MARGIN, METRICS, OVERVIEW_TEXT } from "../constants"
import {
  comparedWithBaseline,
  formatDateTime,
  formatMetric,
  formatPercent,
  shareInWords,
  trainingDataLabel,
} from "../utils"
import { StatusBadge } from "./StatusBadge"

function Detail({ label, children }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

/** Plain sentences built from the metadata test metrics (nothing hardcoded). */
function reliabilitySentences(model) {
  const metrics = model.test_metrics || {}
  const sentences = []
  const recall = shareInWords(metrics.High_Recall)
  if (recall) {
    sentences.push(
      `In testing, it found about ${recall} households that later became High risk (High recall ${formatPercent(metrics.High_Recall, 0)}).`,
    )
  }
  const precision = shareInWords(metrics.High_Precision)
  if (precision) {
    sentences.push(
      `When it said High, it was right about ${precision} times (High precision ${formatPercent(metrics.High_Precision, 0)}).`,
    )
  }
  const comparison = comparedWithBaseline(
    metrics.Macro_F1,
    model.persistence_baseline_test_macro_f1,
    BASELINE_SIMILAR_MARGIN,
  )
  if (comparison) {
    sentences.push(
      `Compared with guessing "same as last visit", it did ${comparison} (Macro-F1 ${formatMetric(metrics.Macro_F1, 2)} vs ${formatMetric(model.persistence_baseline_test_macro_f1, 2)}).`,
    )
  }
  if (/no embargo/i.test(model.validation_methodology || "")) sentences.push(OVERVIEW_TEXT.notEmbargoed)
  return sentences
}

function TechnicalDetails({ model }) {
  const metrics = model.test_metrics || {}
  const period = model.training_period || {}
  const simulated = /synthetic/i.test(model.data_basis || "")

  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-medium">
        Technical details (for reviewers)
        <ChevronDown className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-5 border-t p-4">
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
                  {key === "Macro_F1" ? formatMetric(model.persistence_baseline_test_macro_f1) : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <dl className="grid gap-3 sm:grid-cols-2">
          <Detail label="Training data">
            {trainingDataLabel(model.data_basis)}
            {simulated && " (simulated panel)"}
          </Detail>
          <Detail label="Created">{formatDateTime(model.created)}</Detail>
          <Detail label="Prediction months">{period.prediction_months || "—"}</Detail>
          <Detail label="Target months">{period.target_months || "—"}</Detail>
          <Detail label="Model">
            {model.model_name} · {model.algorithm}
          </Detail>
          <Detail label="Status">{model.model_status}</Detail>
        </dl>

        {model.validation_methodology && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">How it was tested</p>
            <p className="text-sm">{model.validation_methodology}</p>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">About the data</p>
          {ABOUT_DATA.map((paragraph) => (
            <p key={paragraph} className="text-sm">
              {paragraph}
            </p>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function ModelMetricsCard({ model }) {
  const sentences = reliabilitySentences(model)

  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{model.horizon} model</CardTitle>
          <StatusBadge status={model.model_status} />
        </div>
        <CardDescription>Risk class {model.horizon_months} months after the visit</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm font-medium">How reliable is it?</p>
          {sentences.length ? (
            <ul className="list-disc space-y-1.5 pl-5 text-sm">
              {sentences.map((sentence) => (
                <li key={sentence}>{sentence}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No test results reported.</p>
          )}
          <p className="text-xs text-muted-foreground">{OVERVIEW_TEXT.reliabilityFooter}</p>
        </div>
        <TechnicalDetails model={model} />
      </CardContent>
    </Card>
  )
}
