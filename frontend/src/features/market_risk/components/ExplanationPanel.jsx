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
import { PageState } from "./PageState"
import { ShapChart } from "./ShapChart"

function HorizonExplanation({ explanation }) {
  const blankFactor = explanation.high_risk_factors.some((factor) => factor.value === null)
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
      <ShapChart factors={explanation.high_risk_factors} />
      {blankFactor && (
        <p className="text-xs text-muted-foreground">
          Some top factors were blank inputs. The model filled them with the
          training median, so a blank answer is not neutral.
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
