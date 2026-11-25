import { useMutation } from "@tanstack/react-query"

import { scoreV2Visit } from "../api/riskV2Api"

/** POST /risk/visit. A mutation, because each check is a new request (nothing is stored). */
export function useV2Visit() {
  return useMutation({ mutationFn: scoreV2Visit, retry: false })
}
