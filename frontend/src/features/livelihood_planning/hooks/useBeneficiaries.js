import { useQuery } from "@tanstack/react-query"

import { getBeneficiaries } from "../api/livelihoodApi"

export function useBeneficiaries() {
  return useQuery({
    queryKey: ["livelihood-beneficiaries"],
    queryFn: getBeneficiaries,
  })
}
