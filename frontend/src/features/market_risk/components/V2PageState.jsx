import { AlertCircle, Inbox } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * Loading / error / empty state for the v2 pages. The error text is the message from api(),
 * which already holds the backend `detail` (e.g. the 503 "no data for this month" text).
 */
export function V2PageState({ loading = false, error, empty = false, emptyMessage = "Nothing to show.", onRetry, rows = 3 }) {
  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    )
  }
  if (error) {
    return (
      <Card role="alert">
        <CardContent className="flex flex-col items-start gap-3 p-5 sm:flex-row sm:items-center">
          <AlertCircle className="size-5 shrink-0 text-destructive" aria-hidden="true" />
          <div className="min-w-0 flex-1 space-y-1 text-sm">
            <p className="font-medium">This could not be loaded.</p>
            <p className="break-words text-muted-foreground">{error.message || "The request could not be completed."}</p>
          </div>
          {onRetry && (
            <Button type="button" variant="outline" onClick={onRetry}>
              Try again
            </Button>
          )}
        </CardContent>
      </Card>
    )
  }
  if (empty) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
          <Inbox className="size-5 shrink-0" aria-hidden="true" />
          <p>{emptyMessage}</p>
        </CardContent>
      </Card>
    )
  }
  return null
}
