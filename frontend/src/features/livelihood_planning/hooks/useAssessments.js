import { useQuery } from "@tanstack/react-query"

import { getAssessments } from "../api/livelihoodApi"

export function useAssessments(beneficiaryId) {
  return useQuery({
    queryKey: ["livelihood-assessments", String(beneficiaryId || "")],
    queryFn: () => getAssessments(beneficiaryId),
    enabled: Boolean(beneficiaryId),
  })
}
