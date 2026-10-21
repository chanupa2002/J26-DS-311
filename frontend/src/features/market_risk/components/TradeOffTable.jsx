import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { TRADE_OFF } from "../constants"
import { formatMetric, formatSigned } from "../utils"

export function TradeOffTable() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Version 2.0 trade-off</CardTitle>
        <CardDescription>
          {TRADE_OFF.decision}. {TRADE_OFF.reason}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Horizon</TableHead>
              <TableHead>Metric</TableHead>
              <TableHead className="text-right">Version 1.0</TableHead>
              <TableHead className="text-right">Version 2.0</TableHead>
              <TableHead className="text-right">Change</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {TRADE_OFF.rows.map((row) => {
              const change = row.current - row.previous
              return (
                <TableRow key={`${row.horizon}-${row.metric}`}>
                  <TableCell>{row.horizon}</TableCell>
                  <TableCell>{row.metric}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMetric(row.previous)}
                  </TableCell>
                  <TableCell className="text-right font-medium tabular-nums">
                    {formatMetric(row.current)}
                  </TableCell>
                  <TableCell
                    className={
                      change < 0
                        ? "text-right tabular-nums text-destructive"
                        : "text-right tabular-nums"
                    }
                  >
                    {formatSigned(change)}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        <p className="text-xs text-muted-foreground">
          Walk-forward mean over several test months, all test rows.
        </p>
      </CardContent>
    </Card>
  )
}
