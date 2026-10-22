import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { WeakSignalTag } from "@/components/explain/WeakSignalTag"

/** @param {{ text: string, source?: string, evidence?: string, strength?: "clear" | "weak" }} props */
export function EvidenceCard({ text, source, evidence, strength }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle className="text-base">{text}</CardTitle>
        <WeakSignalTag show={strength === "weak"} />
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">
        {source && <p>Source: {source}</p>}
        {evidence && (
          <Tooltip>
            <TooltipTrigger className="text-left underline decoration-dotted underline-offset-4">
              View original evidence
            </TooltipTrigger>
            <TooltipContent className="max-w-sm">{evidence}</TooltipContent>
          </Tooltip>
        )}
      </CardContent>
    </Card>
  )
}
