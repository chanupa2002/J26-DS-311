import { LevelList } from "../components/LevelList"
import { ModelMetricsCard } from "../components/ModelMetricsCard"
import { OverviewIntro } from "../components/OverviewIntro"
import { PageState } from "../components/PageState"
import { ReviewerDetails } from "../components/ReviewerDetails"
import { ValidationNotice } from "../components/ValidationNotice"
import { OVERVIEW_TEXT, PROTOTYPE_REASON } from "../constants"
import { useModelInfo } from "../hooks/useModelInfo"

export function OverviewPage() {
  const modelInfo = useModelInfo()

  if (modelInfo.isPending) return <PageState loading />
  if (modelInfo.isError) {
    return (
      <PageState error={modelInfo.error} onRetry={() => modelInfo.refetch()} />
    )
  }

  const { models = [], features = [], categorical_levels: levels = {} } =
    modelInfo.data || {}

  if (!models.length) {
    return <PageState empty emptyMessage="The backend reported no models." />
  }

  return (
    <div className="space-y-6">
      <ValidationNotice reasons={[PROTOTYPE_REASON]} />

      <OverviewIntro />

      <div className="grid gap-6 lg:grid-cols-2">
        {models.map((model) => (
          <ModelMetricsCard key={model.horizon} model={model} />
        ))}
      </div>
      <p className="-mt-3 text-xs text-muted-foreground">{OVERVIEW_TEXT.reliabilityFooter}</p>

      <div className="grid gap-6 lg:grid-cols-2">
        <LevelList
          title="Livelihood categories"
          description="The livelihood categories the models know."
          levels={levels.F_Category}
        />
        <LevelList
          title="Districts"
          description="The districts the models know."
          levels={levels.F_District}
        />
      </div>

      <ReviewerDetails features={features} />
    </div>
  )
}
