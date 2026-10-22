import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ChevronDown } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { FACTOR_TEXT, SHAP_NOTE, WHY_TEXT } from "../constants"
import { formatPercent } from "../utils"
import { FactorList } from "./FactorList"
import { FeatureName } from "./FeatureName"
import { PageState } from "./PageState"
import { ShapChart } from "./ShapChart"
import { WhyCard } from "./WhyCard"

function HorizonExplanation({ explanation }) {
  const blankFactors = explanation.high_risk_factors.filter((factor) => factor.value === null)
  const blankFactor = blankFactors.length > 0
  // base_value belongs to the explained (= predicted) class, so the start of P(High) is only
  // known exactly when the prediction is High.
  const startLine =
    explanation.explained_class === "High" &&
    Number.isFinite(explanation.base_value) &&
    Number.isFinite(explanation.high_risk_probability)
      ? FACTOR_TEXT.start(formatPercent(explanation.base_value, 0), formatPercent(explanation.high_risk_probability, 0))
      : null
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span>
          {explanation.horizon} model · P(High) ={" "}
          <span className="font-medium text-foreground">
            {formatPercent(explanation.high_risk_probability)}
          </span>
        </span>
      </div>
      <WhyCard explanation={explanation} />
      {startLine && <p className="text-sm text-muted-foreground">{startLine}</p>}
      <FactorList factors={explanation.high_risk_factors} />
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
      <Collapsible className="rounded-lg border">
        <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
          <div className="space-y-0.5">
            <p className="text-sm font-medium">{FACTOR_TEXT.technical}</p>
            <p className="text-xs text-muted-foreground">{FACTOR_TEXT.technicalHelp} {SHAP_NOTE}</p>
          </div>
          <ChevronDown className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
        </CollapsibleTrigger>
        <CollapsibleContent className="border-t p-4">
          <ShapChart factors={explanation.high_risk_factors} />
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

/** SHAP high_risk_factors per horizon. If /explain failed, only this panel shows the error. */
export function ExplanationPanel({ explanation, error, onRetry }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Why this prediction</CardTitle>
        <CardDescription>{WHY_TEXT.note}</CardDescription>
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
