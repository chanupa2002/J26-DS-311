import { useMutation } from "@tanstack/react-query"

import { getSwot } from "../api/livelihoodApi"

export function useSwot() {
  return useMutation({ mutationFn: getSwot })
}
