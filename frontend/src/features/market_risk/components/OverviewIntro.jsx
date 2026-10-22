import { ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import { OVERVIEW_TEXT } from "../constants"

/** "What this tool does" in 2 sentences, and 3 step cards. */
export function OverviewIntro() {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <CardTitle>What this tool does</CardTitle>
        {OVERVIEW_TEXT.intro.map((sentence) => (
          <p key={sentence} className="text-sm text-muted-foreground">
            {sentence}
          </p>
        ))}
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        {OVERVIEW_TEXT.steps.map((step) => (
          <Link
            key={step.title}
            to={step.path}
            className="group flex flex-col justify-between gap-3 rounded-lg border p-4 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="space-y-1">
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-sm text-muted-foreground">{step.text}</p>
            </div>
            <span className="flex items-center gap-1 text-sm font-medium text-primary">
              {step.link}
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}
