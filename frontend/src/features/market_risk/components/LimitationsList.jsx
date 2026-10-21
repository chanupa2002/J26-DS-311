import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { LIMITATIONS, LIMITATIONS_SHOWN } from "../constants"

export function LimitationsList() {
  const [open, setOpen] = useState(false)
  const shown = LIMITATIONS.slice(0, LIMITATIONS_SHOWN)
  const rest = LIMITATIONS.slice(LIMITATIONS_SHOWN)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Limitations</CardTitle>
      </CardHeader>
      <CardContent>
        <Collapsible open={open} onOpenChange={setOpen} className="space-y-3">
          <ul className="list-disc space-y-2 pl-5 text-sm">
            {shown.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <CollapsibleContent>
            <ul className="list-disc space-y-2 pl-5 text-sm">
              {rest.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </CollapsibleContent>
          {rest.length > 0 && (
            <CollapsibleTrigger asChild>
              <Button type="button" variant="outline" size="sm">
                {open ? "Show fewer" : `Show all ${LIMITATIONS.length}`}
              </Button>
            </CollapsibleTrigger>
          )}
        </Collapsible>
      </CardContent>
    </Card>
  )
}
