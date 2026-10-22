import { AssessmentResult } from "../components/AssessmentResult"
import { PageState } from "../components/PageState"
import { ProfileForm } from "../components/ProfileForm"
import { useRecommend } from "../hooks/useRecommend"

export function RecommendPage() {
  const recommendation = useRecommend()

  return (
    <div className="space-y-6">
      <ProfileForm
        onSubmit={(profile) => recommendation.mutate(profile)}
        submitting={recommendation.isPending}
        submitLabel="Get recommendations"
      />

      {recommendation.isPending && <PageState loading />}
      {recommendation.isError && (
        <PageState
          error={recommendation.error}
          onRetry={() => recommendation.mutate(recommendation.variables)}
        />
      )}
      {recommendation.data && <AssessmentResult result={recommendation.data} />}
    </div>
  )
}
