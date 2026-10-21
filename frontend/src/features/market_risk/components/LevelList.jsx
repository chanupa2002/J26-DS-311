import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

/** @param {{ title: string, description?: string, levels?: string[] }} props */
export function LevelList({ title, description, levels = [] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {title} ({levels.length})
        </CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        {levels.length ? (
          levels.map((level) => (
            <Badge key={level} variant="outline">
              {level}
            </Badge>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">No levels reported.</p>
        )}
      </CardContent>
    </Card>
  )
}
