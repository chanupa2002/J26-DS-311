import { Card, CardContent } from "@/components/ui/card"

export function KpiCard({ label, value, hint }) {
  return (
    <Card>
      <CardContent className="space-y-1 p-4">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-3xl font-semibold tabular-nums">{value}</p>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  )
}
