import { TriangleAlert } from "lucide-react"

/** Data warnings returned with a visit (e.g. district outside training data). */
export function WarningsNote({ warnings = [] }) {
  if (!warnings.length) return null
  return (
    <div role="note" className="flex gap-2 rounded-md border border-amber-400 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
      <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <ul className="space-y-0.5">
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </div>
  )
}
