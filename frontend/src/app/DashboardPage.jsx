import { useQueries } from "@tanstack/react-query"
import { ArrowRight, CircleCheck, CircleX } from "lucide-react"
import { Link } from "react-router-dom"

import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { features } from "@/app/features"
import { api } from "@/lib/api"

export function DashboardPage() {
  const healthQueries = useQueries({
    queries: features.map((feature) => ({
      queryKey: ["component-health", feature.key],
      queryFn: () => api(feature.healthPath),
      staleTime: 30_000,
    })),
  })
  const today = new Intl.DateTimeFormat("en", {
    dateStyle: "full",
  }).format(new Date())
  const quickLinkFeatures = features.filter(
    (feature) => feature.nav.items.length > 0,
  )

  return (
    <div className="space-y-8">
      <PageHeader title="Welcome, Admin" description={today} />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Component status
        </h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {features.map((feature, index) => {
            const query = healthQueries[index]
            const connected = query.isSuccess
            return (
              <Card key={feature.key}>
                <CardHeader className="flex-row items-center justify-between gap-3">
                  <CardTitle className="text-base">
                    {feature.nav.title}
                  </CardTitle>
                  <feature.nav.icon className="size-5 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  {query.isPending ? (
                    <Skeleton className="h-6 w-28" />
                  ) : (
                    <Badge variant={connected ? "secondary" : "outline"}>
                      {connected ? (
                        <CircleCheck className="mr-1 size-3.5" />
                      ) : (
                        <CircleX className="mr-1 size-3.5" />
                      )}
                      {connected ? "Connected" : "Not connected"}
                    </Badge>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Quick links
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {quickLinkFeatures.map((feature) => {
            const firstItem = feature.nav.items[0]
            return (
              <Link key={feature.key} to={firstItem.path} className="group">
                <Card className="h-full transition-colors group-hover:border-foreground/20 group-hover:bg-muted/30">
                  <CardContent className="flex items-center gap-4 p-5">
                    <div className="rounded-lg bg-muted p-3">
                      <feature.nav.icon className="size-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{feature.nav.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {firstItem.title}
                      </p>
                    </div>
                    <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      </section>
    </div>
  )
}
