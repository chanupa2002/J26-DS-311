import { ArrowRight, ClipboardList } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

import { formatReason } from "../utils"
import { RiskBadge } from "./RiskBadge"

function PossibleRange({ result }) {
  const { best_case_class: best, worst_case_class: worst } = result
  if (best === worst) {
    return (
      <p className="text-sm text-muted-foreground">
        Possible range: <RiskBadge riskClass={best} />{" "}
        {result.unknown_count > 0
          ? "(the blank answers cannot change it)"
          : "(all answers given)"}
      </p>
    )
  }
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      Possible range: <RiskBadge riskClass={best} />
      <span aria-hidden="true">–</span>
      <span className="sr-only">to</span>
      <RiskBadge riskClass={worst} />
      <span>(best case if blanks are No, worst case if blanks are Yes)</span>
    </p>
  )
}

export function CurrentRiskResult({ result, stale = false, onUseInFutureRisk }) {
  return (
    <Card aria-live="polite">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1.5">
            <CardTitle>Current risk class</CardTitle>
            <CardDescription>
              {result.signal_count} of 3 signals Yes · {result.unknown_count}{" "}
              not answered
            </CardDescription>
          </div>
          <RiskBadge riskClass={result.risk_class} size="lg" />
        </div>
        <PossibleRange result={result} />
        {stale && (
          <p className="text-xs text-muted-foreground">
            The answers have changed since this check. Press Check risk to
            update.
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-5">
        {result.follow_up_needed && (
          <div
            role="status"
            className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-50/60 p-4 text-sm dark:bg-amber-950/20"
          >
            <ClipboardList className="mt-0.5 size-5 shrink-0 text-amber-700 dark:text-amber-400" />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium">Follow-up visit recommended</p>
              </div>
              <p className="text-muted-foreground">
                Some answers are blank and could change the class (
                {result.possible_range.replace("-", " – ")}). Ask the missing
                questions at the next visit.
              </p>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-sm font-medium">Reasons</p>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {result.reasons.map((reason) => (
              <li key={reason}>{formatReason(reason)}</li>
            ))}
          </ul>
        </div>

        <Separator />
        <p className="text-xs text-muted-foreground">
          Rule: {result.rule_version}
        </p>
      </CardContent>

      <CardFooter className="justify-end">
        <Button type="button" variant="outline" onClick={onUseInFutureRisk}>
          Use in Future Risk
          <ArrowRight className="size-4" />
        </Button>
      </CardFooter>
    </Card>
  )
}
