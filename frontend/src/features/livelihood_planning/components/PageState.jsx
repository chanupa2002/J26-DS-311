import { AlertCircle, Inbox } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function PageState({
  loading = false,
  error,
  empty = false,
  onRetry,
  emptyMessage = "No records found.",
}) {
  if (loading) {
    return (
      <div className="space-y-3" aria-label="Loading">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <Card role="alert">
        <CardContent className="flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center">
          <AlertCircle className="size-5 shrink-0 text-destructive" />
          <p className="min-w-0 flex-1 text-sm">
            {error.message || "The request could not be completed."}
          </p>
          {onRetry && (
            <Button type="button" variant="outline" onClick={onRetry}>
              Retry
            </Button>
          )}
        </CardContent>
      </Card>
    )
  }

  if (empty) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-6 text-sm text-muted-foreground">
          <Inbox className="size-5 shrink-0" />
          <p>{emptyMessage}</p>
        </CardContent>
      </Card>
    )
  }

  return null
}
