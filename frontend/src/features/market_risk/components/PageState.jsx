import { AlertCircle, Inbox, ServerCrash, WifiOff } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

import { errorKind } from "../utils"

const ERROR_TEXT = {
  unavailable: {
    icon: ServerCrash,
    title:
      "This market-risk service is not available on the server right now. Contact the market_risk owner.",
  },
  network: {
    icon: WifiOff,
    title: "Cannot reach the backend. Check that it is running and VITE_API_URL is correct.",
  },
  invalid: {
    icon: AlertCircle,
    title: "The request was not accepted:",
  },
}

export function PageState({
  loading = false,
  error,
  empty = false,
  onRetry,
  emptyMessage = "Nothing to show.",
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
    const { icon: Icon, title } = ERROR_TEXT[errorKind(error)]
    return (
      <Card role="alert">
        <CardContent className="flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center">
          <Icon className="size-5 shrink-0 text-destructive" />
          <div className="min-w-0 flex-1 space-y-1 text-sm">
            <p className="font-medium">{title}</p>
            <p className="text-muted-foreground">
              {error.message || "The request could not be completed."}
            </p>
          </div>
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
