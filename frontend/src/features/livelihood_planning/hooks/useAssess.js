import { useMutation, useQueryClient } from "@tanstack/react-query"

import { assessBeneficiary } from "../api/livelihoodApi"

export function useAssess() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (beneficiaryId) => assessBeneficiary(beneficiaryId),
    onSuccess: (assessment) => {
      queryClient.invalidateQueries({
        queryKey: ["livelihood-assessments", String(assessment.beneficiary_id)],
      })
    },
  })
}
