import { useMutation, useQuery } from "@tanstack/react-query"

import { getSwot } from "../api/livelihoodApi"

export function useSwot() {
  return useMutation({ mutationFn: (profile) => getSwot(profile) })
}

export function useSelectedSwot(profile, livelihood, enabled) {
  return useQuery({
    queryKey: ["livelihood-swot", profile || {}, livelihood || ""],
    queryFn: () => getSwot(profile, livelihood),
    enabled,
    retry: false,
    staleTime: Infinity,
  })
}
