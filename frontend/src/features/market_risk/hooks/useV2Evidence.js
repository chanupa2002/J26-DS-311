import { useQuery } from "@tanstack/react-query"

import { getV2ModelEvidence } from "../api/riskV2Api"

export function useV2Evidence() {
  return useQuery({
    queryKey: ["risk-v2-evidence"],
    queryFn: getV2ModelEvidence,
    staleTime: Infinity,
    retry: false,
  })
}
