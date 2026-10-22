import { Info } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import { splitFeatureNames } from "../utils"
import { FeatureName } from "./FeatureName"

export function WarningList({ warnings = [] }) {
  if (!warnings.length) return null

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Info className="size-4 text-muted-foreground" />
          Input notes ({warnings.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {warnings.map((warning) => (
            <li key={warning} className="break-words">
              {splitFeatureNames(
                warning.replace("were null and will be median-imputed", "were not answered; the model uses the typical value for"),
              ).map((part, i) =>
                typeof part === "string" ? part : <FeatureName key={i} name={part.feature} />,
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
