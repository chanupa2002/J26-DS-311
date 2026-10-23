import { ConfidenceBadge } from "@/components/explain/ConfidenceBadge"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { LOW_CONFIDENCE_PROBABILITY, VALIDATION_REASON } from "../constants"
import { ProbabilityBars } from "./ProbabilityBars"
import { RiskBadge } from "./RiskBadge"

/** "Low confidence" (weak-signal flag or top probability < 0.5), else "Validation pending". */
function PredictionBadge({ prediction, weakSignal }) {
  const top = Math.max(...Object.values(prediction.probabilities || {}).map(Number))
  if (weakSignal || !(top >= LOW_CONFIDENCE_PROBABILITY)) return <ConfidenceBadge level="low" />
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="outline">Validation pending</Badge>
      </TooltipTrigger>
      <TooltipContent>{VALIDATION_REASON}</TooltipContent>
    </Tooltip>
  )
}

export function PredictionCard({ prediction, weakSignal = false }) {
  const months = prediction.horizon === "6M" ? 6 : 3

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1.5">
            <CardTitle>{prediction.horizon} prediction</CardTitle>
            <CardDescription>Risk class {months} months ahead</CardDescription>
          </div>
          <PredictionBadge prediction={prediction} weakSignal={weakSignal} />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Predicted class</span>
          <RiskBadge riskClass={prediction.predicted_risk} size="lg" />
        </div>
      </CardHeader>
      <CardContent>
        <ProbabilityBars
          probabilities={prediction.probabilities}
          predicted={prediction.predicted_risk}
        />
      </CardContent>
    </Card>
  )
}
