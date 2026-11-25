import { Link } from "react-router-dom"

import { Card, CardContent } from "@/components/ui/card"

import { categoryLabel, shortMonth } from "./v2format"

function Step({ number, title, children }) {
  return (
    <li className="flex min-w-0 flex-1 gap-3">
      <span
        aria-hidden="true"
        className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground"
      >
        {number}
      </span>
      <div className="min-w-0 space-y-0.5 text-sm">
        <p className="font-medium">
          <span className="sr-only">Step {number}: </span>
          {title}
        </p>
        <div className="text-muted-foreground">{children}</div>
      </div>
    </li>
  )
}

/** ① livelihood → ② Samurdhi grant → ③ market-risk monitoring (this component). */
export function StepStrip({ category, grantStatusLabel, visits, latestMonth }) {
  return (
    <Card>
      <CardContent className="p-4">
        <ol className="flex flex-col gap-4 md:flex-row md:gap-6">
          <Step number={1} title="Livelihood">
            <p>
              Livelihood being monitored: <span className="text-foreground">{categoryLabel(category)}</span>
            </p>
            <Link to="/livelihood/recommend" className="underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
              Livelihood recommendation
            </Link>
          </Step>
          <Step number={2} title="Samurdhi grant used?">
            <p className="text-foreground">{grantStatusLabel || "Not answered"}</p>
          </Step>
          <Step number={3} title="Monthly risk check (this page)">
            <p>
              {visits} monthly {visits === 1 ? "visit" : "visits"}, latest {shortMonth(latestMonth)}
            </p>
          </Step>
        </ol>
      </CardContent>
    </Card>
  )
}
