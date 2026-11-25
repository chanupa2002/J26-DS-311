import { Check, X } from "lucide-react"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { decimal, METRIC_LABELS } from "./v2format"

/** Model vs "risk stays the same" (persistence) on each test. */
export function EvidenceTable({ comparisons }) {
  return (
    <Table className="min-w-[620px]">
      <TableHeader>
        <TableRow>
          <TableHead>Test</TableHead>
          <TableHead>Metric</TableHead>
          <TableHead className="text-right">Model</TableHead>
          <TableHead className="text-right">Risk stays the same</TableHead>
          <TableHead>Model better?</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {comparisons.map((row) => (
          <TableRow key={row.name}>
            <TableCell className="font-medium">{row.name}</TableCell>
            <TableCell>{METRIC_LABELS[row.metric] || row.metric}</TableCell>
            <TableCell className="text-right tabular-nums">{decimal(row.model)}</TableCell>
            <TableCell className="text-right tabular-nums">{decimal(row.persistence)}</TableCell>
            <TableCell>
              {row.model_better ? (
                <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400">
                  <Check className="size-4" aria-hidden="true" /> Yes
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-red-700 dark:text-red-400">
                  <X className="size-4" aria-hidden="true" /> No
                </span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
