import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { getV2Recommendations, saveV2Decision } from "../api/riskV2Api"

const key = (householdKey) => ["risk-v2-recommendations", householdKey]

export function useV2Recommendations(householdKey) {
  return useQuery({
    queryKey: key(householdKey),
    queryFn: () => getV2Recommendations(householdKey),
    enabled: Boolean(householdKey),
    retry: false,
  })
}

/** Save one decision, then reload the recommendations so the saved decision is shown. */
export function useV2Decision(householdKey) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ruleId, body }) => saveV2Decision(householdKey, ruleId, body),
    retry: false,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key(householdKey) }),
  })
}
