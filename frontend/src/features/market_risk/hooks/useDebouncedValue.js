import { useEffect, useState } from "react"

export const DEBOUNCE_MS = 400

/** `value` after it has not changed for `delay` ms. */
export function useDebouncedValue(value, delay = DEBOUNCE_MS) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}
