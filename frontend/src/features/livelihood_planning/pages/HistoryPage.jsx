import { ChevronDown } from "lucide-react"
import { useMemo, useState } from "react"

import { ConfidenceBadge } from "@/components/explain/ConfidenceBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { AssessmentResult } from "../components/AssessmentResult"
import { BeneficiarySelect } from "../components/BeneficiarySelect"
import { PageState } from "../components/PageState"
import { useAssessments } from "../hooks/useAssessments"
import { useBeneficiaries } from "../hooks/useBeneficiaries"
import { scoreOutOf100, titleCaseLivelihood } from "../utils"

function formatDate(value) {
  if (!value) return "Date unavailable"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "Date unavailable"
  return new Intl.DateTimeFormat("en-LK", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}

export function HistoryPage() {
  const [beneficiaryId, setBeneficiaryId] = useState("")
  const beneficiaries = useBeneficiaries()
  const history = useAssessments(beneficiaryId)
  const assessments = useMemo(
    () =>
      [...(history.data || [])].sort(
        (left, right) =>
          new Date(right.created_at || 0).getTime() -
          new Date(left.created_at || 0).getTime(),
      ),
    [history.data],
  )

  if (beneficiaries.isPending) return <PageState loading />
  if (beneficiaries.isError) {
    return (
      <PageState
        error={beneficiaries.error}
        onRetry={() => beneficiaries.refetch()}
      />
    )
  }
  if (!beneficiaries.data?.length) {
    return <PageState empty emptyMessage="No beneficiaries found." />
  }

  return (
    <div className="space-y-6">
      <BeneficiarySelect
        beneficiaries={beneficiaries.data}
        value={beneficiaryId}
        onChange={setBeneficiaryId}
      />

      {history.isPending && <PageState loading />}
      {history.isError && (
        <PageState error={history.error} onRetry={() => history.refetch()} />
      )}
      {beneficiaryId && history.isSuccess && !assessments.length && (
        <PageState empty emptyMessage="No saved assessments found." />
      )}

      {assessments.length > 0 && (
        <div className="space-y-3">
          {assessments.map((assessment) => (
            <Collapsible key={assessment.id}>
              <Card>
                <CollapsibleTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    className="group h-auto w-full justify-start rounded-xl p-0 text-left"
                  >
                    <CardContent className="grid w-full gap-3 p-5 sm:grid-cols-[1fr_auto_auto_auto_auto] sm:items-center">
                      <div>
                        <p className="font-medium">
                          {titleCaseLivelihood(assessment.chosen_livelihood)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(assessment.created_at)}
                        </p>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        Viability{" "}
                        {assessment.viability
                          ? scoreOutOf100(assessment.viability.score).toFixed(1)
                          : "—"}
                      </span>
                      <ConfidenceBadge level={assessment.confidence} />
                      <Badge variant="outline">{assessment.status}</Badge>
                      <ChevronDown className="transition-transform group-data-[state=open]:rotate-180" />
                    </CardContent>
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="border-t p-5">
                  <AssessmentResult result={assessment} saved />
                </CollapsibleContent>
              </Card>
            </Collapsible>
          ))}
        </div>
      )}
    </div>
  )
}
