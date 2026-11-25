import { useQuery } from "@tanstack/react-query"

import { getV2Households } from "../api/riskV2Api"

/** Households list for a month (undefined = latest). No automatic retry: errors show at once. */
export function useV2Households(month) {
  return useQuery({
    queryKey: ["risk-v2-households", month ?? "latest"],
    queryFn: () => getV2Households(month),
    retry: false,
  })
}
