import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { AlertBadge } from "./AlertBadge"
import { InfoTip } from "./InfoTip"
import { MarketPill } from "./MarketPill"
import { ProbabilityBar } from "./ProbabilityBar"
import { RiskPill } from "./RiskPill"
import { categoryLabel, inTen, percent } from "./v2format"

const COLUMNS = [
  { label: "Household", tip: "The household code, its livelihood and its district." },
  { label: "Grant used?", tip: "Whether the Samurdhi grant has been received and used, from the latest visit form." },
  { label: "Risk this month", tip: "Worked out automatically from this month's visit form – it is not a prediction." },
  { label: "Why", tip: "The answers on this month's visit form that led to this month's risk.", className: "min-w-40" },
  {
    label: "Next month",
    tip: "Based on past visits: how often households in this risk class were High the next month. Not a prediction model.",
    className: "min-w-32",
  },
  { label: "Expected in 3 months", tip: "The risk level the model expects for this household in 3 months." },
  {
    label: "Chance of High risk in 3 months",
    tip: "How likely the model thinks this household will be High risk in 3 months. The marker shows the level that raises an alert, learned from past data.",
    className: "min-w-36",
  },
  { label: "Needs attention?", tip: "Yes when the chance of High risk in 3 months reaches the alert level learned from past data." },
  { label: "Market prices", tip: "Whether prices for this livelihood in this district moved unusually: Normal, Moderate or High pressure." },
]

function Head({ label, tip, className }) {
  return (
    <TableHead className={className}>
      <span className="inline-flex items-center gap-1 whitespace-normal leading-tight">
        {label}
        <InfoTip label={label}>{tip}</InfoTip>
      </span>
    </TableHead>
  )
}

/** Most likely class next month and the chance of High, from past monthly transitions. */
function NextMonth({ riskClass, pHigh }) {
  if (!riskClass) return <span className="text-xs text-muted-foreground">Unknown – form incomplete</span>
  return (
    <div className="space-y-1">
      <RiskPill riskClass={riskClass} />
      <p className="whitespace-nowrap text-xs" title={`Past visits: ${percent(pHigh, 1)} were High the next month`}>
        {inTen(pHigh)} High
      </p>
    </div>
  )
}

export function HouseholdsTable({ households, alertThreshold }) {
  return (
    <Table className="min-w-[1040px]">
      <TableHeader>
        <TableRow>
          {COLUMNS.map((column) => (
            <Head key={column.label} {...column} />
          ))}
          <TableHead>
            <span className="sr-only">Open</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {households.map((row) => {
          const detail = `/risk/v2/household/${encodeURIComponent(row.household_key)}`
          return (
            <TableRow key={row.household_key}>
              <TableCell>
                <Link to={detail} className="font-medium underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring">
                  {row.household_key}
                </Link>
                <p className="text-xs text-muted-foreground">
                  {categoryLabel(row.category)} · {row.district}
                </p>
              </TableCell>
              <TableCell className="text-sm">{row.grant_status_label || "Not answered"}</TableCell>
              <TableCell>
                <RiskPill riskClass={row.current_risk} />
              </TableCell>
              <TableCell className="text-xs">{row.reasons.join("; ")}</TableCell>
              <TableCell>
                <NextMonth riskClass={row.next_month_class} pHigh={row.next_month_p_high} />
              </TableCell>
              <TableCell>
                <RiskPill riskClass={row.predicted_3m} />
              </TableCell>
              <TableCell>
                <ProbabilityBar value={row.p_high_3m} threshold={alertThreshold} compact />
              </TableCell>
              <TableCell>
                <AlertBadge alert={row.alert_3m} />
              </TableCell>
              <TableCell>
                <MarketPill level={row.market_level} />
              </TableCell>
              <TableCell>
                <Button asChild size="sm" variant="outline">
                  <Link to={detail} aria-label={`View ${row.household_key}`}>
                    View
                  </Link>
                </Button>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
