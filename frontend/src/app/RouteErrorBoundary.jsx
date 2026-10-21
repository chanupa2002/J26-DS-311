import { Link, useRouteError } from "react-router-dom"

import { Button } from "@/components/ui/button"

export function RouteErrorBoundary() {
  const error = useRouteError()
  const message =
    error instanceof Error ? error.message : "This page could not be loaded."
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="max-w-lg text-sm text-muted-foreground">{message}</p>
      <Button asChild>
        <Link to="/">Return to dashboard</Link>
      </Button>
    </div>
  )
}
