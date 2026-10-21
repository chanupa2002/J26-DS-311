import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { ABOUT_DATA } from "../constants"

export function AboutDataCard() {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CardHeader className="flex-row items-center justify-between gap-3">
          <div className="space-y-1.5">
            <CardTitle>About the data</CardTitle>
            <CardDescription>{ABOUT_DATA.summary}</CardDescription>
          </div>
          <CollapsibleTrigger asChild>
            <Button type="button" variant="outline" size="sm">
              {open ? "Hide" : "Read more"}
            </Button>
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="space-y-3 text-sm">
            {ABOUT_DATA.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
