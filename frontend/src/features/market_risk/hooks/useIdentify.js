import { useMutation } from "@tanstack/react-query"

import { identifyCurrentRisk } from "../api/riskApi"

export function useIdentify() {
  return useMutation({ mutationFn: identifyCurrentRisk })
}
