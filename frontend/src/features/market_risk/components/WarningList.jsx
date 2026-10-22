import { Info } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

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
              {warning}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
