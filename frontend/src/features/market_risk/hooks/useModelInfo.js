import { useQuery } from "@tanstack/react-query"

import { getRiskModelInfo } from "../api/riskApi"

export function useModelInfo() {
  return useQuery({
    queryKey: ["risk-model-info"],
    queryFn: getRiskModelInfo,
    staleTime: Infinity,
  })
}
