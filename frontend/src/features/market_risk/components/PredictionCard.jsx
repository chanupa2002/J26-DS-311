import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import { ProbabilityBars } from "./ProbabilityBars"
import { RiskBadge } from "./RiskBadge"

export function PredictionCard({ prediction }) {
  const months = prediction.horizon === "6M" ? 6 : 3

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="space-y-1.5">
          <CardTitle>{prediction.horizon} prediction</CardTitle>
          <CardDescription>
            Risk class {months} months ahead · {prediction.model_name}
          </CardDescription>
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
