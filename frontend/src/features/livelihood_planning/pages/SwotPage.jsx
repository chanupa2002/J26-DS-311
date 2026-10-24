import { AssessmentResult } from "../components/AssessmentResult"
import { PageState } from "../components/PageState"
import { ProfileForm } from "../components/ProfileForm"
import { useSwot } from "../hooks/useSwot"

export function SwotPage() {
  const swot = useSwot()

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">Results are not saved.</p>
      <ProfileForm
        onSubmit={(profile) => swot.mutate(profile)}
        submitting={swot.isPending}
        submitLabel="Generate SWOT"
      />

      {swot.isPending && <PageState loading />}
      {swot.isError && (
        <PageState
          error={swot.error}
          onRetry={() => swot.mutate(swot.variables)}
        />
      )}
      {swot.data && (
        <AssessmentResult
          key={swot.submittedAt}
          result={swot.data}
          profile={swot.variables}
          selectable
          trailDefaultOpen
        />
      )}
    </div>
  )
}
