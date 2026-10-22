import { useSyncExternalStore } from "react"

/**
 * The answers of the last Risk Check, kept in memory only (module-level store): it survives
 * moving between pages, but a page refresh clears it. Nothing is written to browser storage.
 * Shape: { signals: { business_not_running, no_profit_last_month, not_progressing_well,
 * market_stress_any } (each 0, 1 or null), savedAt: epoch ms } or null.
 */
let lastRiskCheck = null
const listeners = new Set()

function emit() {
  for (const listener of listeners) listener()
}

function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getLastRiskCheck() {
  return lastRiskCheck
}

export function saveLastRiskCheck(signals) {
  lastRiskCheck = { signals: { ...signals }, savedAt: Date.now() }
  emit()
}

export function clearLastRiskCheck() {
  lastRiskCheck = null
  emit()
}

export function useLastRiskCheck() {
  return useSyncExternalStore(subscribe, getLastRiskCheck)
}
