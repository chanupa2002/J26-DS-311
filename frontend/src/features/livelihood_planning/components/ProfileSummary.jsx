import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import { displayValue } from "../utils"

const FIELDS = [
  ["id", "ID"],
  ["full_name", "Name"],
  ["district", "District"],
  ["age", "Age"],
  ["gender", "Gender"],
  ["female_headed", "Female-headed"],
  ["disability", "Disability"],
  ["aswesuma_category", "Aswesuma category"],
]

export function ProfileSummary({ profile }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Profile</CardTitle>
        {profile?.is_demo === true && <Badge variant="secondary">Demo</Badge>}
      </CardHeader>
      <CardContent>
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FIELDS.map(([key, label]) => (
            <div key={key} className="space-y-1">
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {label}
              </dt>
              <dd className="text-sm font-medium">
                {displayValue(profile[key])}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  )
}
