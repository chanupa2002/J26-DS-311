import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

import { RiskPill } from "./RiskPill"
import { inTen, percent } from "./v2format"

/**
 * "How risk changes from one month to the next": the monthly transition matrix from
 * /model/evidence, as "about x in 10". The exact % and the visit count are in the tooltip.
 * Cells on the diagonal (risk stays the same) are bold and say "stays".
 */
export function TransitionTable({ transitions }) {
  const { classes = [], matrix = [], counts = [] } = transitions ?? {}
  return (
    <Table className="min-w-[340px]">
      <TableHeader>
        <TableRow>
          <TableHead>This month</TableHead>
          {classes.map((name) => (
            <TableHead key={name}>Next month {name}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {classes.map((from, i) => {
          const rowTotal = (counts[i] ?? []).reduce((sum, value) => sum + value, 0)
          return (
            <TableRow key={from}>
              <TableCell>
                <RiskPill riskClass={from} />
                <p className="mt-1 text-xs text-muted-foreground">{rowTotal} changes seen</p>
              </TableCell>
              {classes.map((to, j) => {
                const value = matrix[i]?.[j]
                const stays = i === j
                return (
                  <TableCell key={to}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span
                          tabIndex={0}
                          className={`inline-block rounded text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${stays ? "font-semibold" : ""}`}
                        >
                          {inTen(value)}
                          {stays && <span className="block text-xs font-normal text-muted-foreground">stays {from}</span>}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent className="text-xs">
                        <p>
                          {from} → {to} next month: {percent(value, 1)}
                        </p>
                        <p>
                          Seen {counts[i]?.[j] ?? 0} of {rowTotal} times (+1 smoothing)
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TableCell>
                )
              })}
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
