import { useMutation } from "@tanstack/react-query"

import { getRecommendations } from "../api/livelihoodApi"

export function useRecommend() {
  return useMutation({ mutationFn: getRecommendations })
}
