import { useQuery } from "@tanstack/react-query"

import { getV2Household } from "../api/riskV2Api"

export function useV2Household(householdKey) {
  return useQuery({
    queryKey: ["risk-v2-household", householdKey],
    queryFn: () => getV2Household(householdKey),
    enabled: Boolean(householdKey),
    retry: false,
  })
}
