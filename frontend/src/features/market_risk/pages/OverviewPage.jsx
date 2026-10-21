import { AboutDataCard } from "../components/AboutDataCard"
import { FeatureList } from "../components/FeatureList"
import { LevelList } from "../components/LevelList"
import { LimitationsList } from "../components/LimitationsList"
import { ModelMetricsCard } from "../components/ModelMetricsCard"
import { PageState } from "../components/PageState"
import { TradeOffTable } from "../components/TradeOffTable"
import { ValidationNotice } from "../components/ValidationNotice"
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
      <ValidationNotice models={models} />

      <AboutDataCard />

      <div className="grid gap-6 lg:grid-cols-2">
        {models.map((model) => (
          <ModelMetricsCard key={model.horizon} model={model} />
        ))}
      </div>

      <TradeOffTable />

      <div className="grid gap-6 lg:grid-cols-2">
        <LevelList
          title="Livelihood categories"
          description="Category levels the models were trained on (F_Category)."
          levels={levels.F_Category}
        />
        <LevelList
          title="Districts"
          description="District levels the models were trained on (F_District)."
          levels={levels.F_District}
        />
      </div>

      <LimitationsList />

      <FeatureList features={features} />
    </div>
  )
}
