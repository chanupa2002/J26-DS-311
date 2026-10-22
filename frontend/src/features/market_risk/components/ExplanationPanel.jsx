import { WeakSignalTag } from "@/components/explain/WeakSignalTag"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { SHAP_NOTE } from "../constants"
import { formatPercent } from "../utils"
import { FeatureName } from "./FeatureName"
import { PageState } from "./PageState"
import { ShapChart } from "./ShapChart"
import { WhyCard } from "./WhyCard"

function HorizonExplanation({ explanation }) {
  const blankFactors = explanation.high_risk_factors.filter((factor) => factor.value === null)
  const blankFactor = blankFactors.length > 0
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span>
          {explanation.horizon} model · P(High) ={" "}
          <span className="font-medium text-foreground">
            {formatPercent(explanation.high_risk_probability)}
          </span>
        </span>
        {blankFactor && <WeakSignalTag />}
      </div>
      <WhyCard explanation={explanation} />
      <ShapChart factors={explanation.high_risk_factors} />
      {blankFactor && (
        <p className="text-xs text-muted-foreground">
          Not answered, so the model used the typical value:{" "}
          {blankFactors.map((factor, i) => (
            <span key={factor.feature}>
              {i > 0 && ", "}
              <FeatureName name={factor.feature} />
            </span>
          ))}
          . A blank answer is not neutral.
        </p>
      )}
    </div>
  )
}

/** SHAP high_risk_factors per horizon. If /explain failed, only this panel shows the error. */
export function ExplanationPanel({ explanation, error, onRetry }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>What pushed the model towards High</CardTitle>
        <CardDescription>{SHAP_NOTE}</CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <PageState error={error} onRetry={onRetry} />
        ) : explanation?.explanations?.length > 1 ? (
          <Tabs defaultValue={explanation.explanations[0].horizon}>
            <TabsList>
              {explanation.explanations.map((item) => (
                <TabsTrigger key={item.horizon} value={item.horizon}>
                  {item.horizon}
                </TabsTrigger>
              ))}
            </TabsList>
            {explanation.explanations.map((item) => (
              <TabsContent key={item.horizon} value={item.horizon} className="pt-4">
                <HorizonExplanation explanation={item} />
              </TabsContent>
            ))}
          </Tabs>
        ) : explanation?.explanations?.length === 1 ? (
          <HorizonExplanation explanation={explanation.explanations[0]} />
        ) : (
          <PageState empty emptyMessage="No explanation returned." />
        )}
      </CardContent>
    </Card>
  )
}
