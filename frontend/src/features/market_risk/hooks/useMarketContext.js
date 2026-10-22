import { useQuery } from "@tanstack/react-query"

import { getMarketContext } from "../api/riskApi"

/** Market + macro features for (category, month); runs only when both are set. */
export function useMarketContext(category, month) {
  return useQuery({
    queryKey: ["risk-market-context", category, month],
    queryFn: () => getMarketContext(category, month),
    enabled: Boolean(category && month),
    staleTime: Infinity,
    retry: false,
  })
}

/**
 * The months with market/macro data. The backend returns them with every
 * market-context answer, so this asks once for the current month of a known category.
 */
export function useMarketMonths(category) {
  const now = new Date()
  const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
  return useQuery({
    queryKey: ["risk-market-months"],
    queryFn: () => getMarketContext(category, month),
    enabled: Boolean(category),
    staleTime: Infinity,
    select: (data) => data.available_months || [],
  })
}
