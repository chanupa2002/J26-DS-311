import { useNavigate, useParams } from "react-router-dom"

import { Button } from "@/components/ui/button"

import { AssessmentResult } from "../components/AssessmentResult"
import { BeneficiarySelect } from "../components/BeneficiarySelect"
import { PageState } from "../components/PageState"
import { ProfileSummary } from "../components/ProfileSummary"
import { useAssess } from "../hooks/useAssess"
import { useBeneficiaries } from "../hooks/useBeneficiaries"

export function AssessPage() {
  const navigate = useNavigate()
  const { beneficiaryId = "" } = useParams()
  const beneficiaries = useBeneficiaries()
  const assessment = useAssess()
  const rows = beneficiaries.data || []
  const selected = rows.find(
    (beneficiary) => String(beneficiary.id) === String(beneficiaryId),
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
  if (!rows.length) {
    return <PageState empty emptyMessage="No beneficiaries found." />
  }

  const changeBeneficiary = (id) => {
    assessment.reset()
    navigate(id ? `/livelihood/assess/${id}` : "/livelihood/assess")
  }

  return (
    <div className="space-y-6">
      <BeneficiarySelect
        beneficiaries={rows}
        value={beneficiaryId}
        onChange={changeBeneficiary}
      />

      {beneficiaryId && !selected && (
        <PageState empty emptyMessage="Beneficiary not found." />
      )}

      {selected && (
        <>
          <ProfileSummary profile={selected} />
          <div className="flex justify-end">
            <Button
              type="button"
              disabled={assessment.isPending}
              onClick={() => assessment.mutate(beneficiaryId)}
            >
              {assessment.isPending ? "Running assessment…" : "Run assessment"}
            </Button>
          </div>
        </>
      )}

      {assessment.isPending && <PageState loading />}
      {assessment.isError && (
        <PageState
          error={assessment.error}
          onRetry={() => assessment.mutate(beneficiaryId)}
        />
      )}
      {assessment.data && <AssessmentResult result={assessment.data} saved />}
    </div>
  )
}
