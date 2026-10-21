import { Card, CardContent } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

/** @param {{ score: number, low: number, high: number }} props */
export function ScoreRange({ score, low, high }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-4 p-4">
        <div>
          <p className="text-xs text-muted-foreground">Viability score</p>
          <p className="text-2xl font-semibold">{score}</p>
        </div>
        <Tooltip>
          <TooltipTrigger className="text-sm text-muted-foreground underline decoration-dotted underline-offset-4">
            {low}–{high}
          </TooltipTrigger>
          <TooltipContent>Stored lower and upper score range.</TooltipContent>
        </Tooltip>
      </CardContent>
    </Card>
  )
}
