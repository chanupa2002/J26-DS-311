import { useQuery } from "@tanstack/react-query"

import { getV2MarketDistricts } from "../api/riskV2Api"

/** Market table for a month (undefined = latest); also gives available_months. */
export function useV2Market(month) {
  return useQuery({
    queryKey: ["risk-v2-market", month ?? "latest"],
    queryFn: () => getV2MarketDistricts(month),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
