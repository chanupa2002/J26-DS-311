import { nav as beneficiarySelectionNav } from "@/features/beneficiary_selection/nav"
import { routes as beneficiarySelectionRoutes } from "@/features/beneficiary_selection/routes"
import { nav as evidenceTrustNav } from "@/features/evidence_trust/nav"
import { routes as evidenceTrustRoutes } from "@/features/evidence_trust/routes"
import { nav as livelihoodPlanningNav } from "@/features/livelihood_planning/nav"
import { routes as livelihoodPlanningRoutes } from "@/features/livelihood_planning/routes"
import { nav as marketRiskNav } from "@/features/market_risk/nav"
import { routes as marketRiskRoutes } from "@/features/market_risk/routes"

export const features = [
  {
    key: "beneficiary_selection",
    nav: beneficiarySelectionNav,
    routes: beneficiarySelectionRoutes,
    healthPath: "/api/beneficiary/health",
  },
  {
    key: "evidence_trust",
    nav: evidenceTrustNav,
    routes: evidenceTrustRoutes,
    healthPath: "/api/trust/health",
  },
  {
    key: "livelihood_planning",
    nav: livelihoodPlanningNav,
    routes: livelihoodPlanningRoutes,
    healthPath: "/api/livelihood/health",
  },
  {
    key: "market_risk",
    nav: marketRiskNav,
    routes: marketRiskRoutes,
    healthPath: "/api/risk/health",
  },
]

export const featureRoutes = features.flatMap((feature) => feature.routes)
