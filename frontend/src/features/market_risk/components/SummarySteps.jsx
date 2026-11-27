import { Sparkles } from "lucide-react"

import { sourceShortName } from "./v2format"

/** Optional AI steps for the officer: numbered, each citing the official passages it is based on. */
export function SummarySteps({ steps, sources = [], onCite }) {
  if (!steps?.length) return null
  const byId = Object.fromEntries(sources.map((source) => [source.chunk_id, source]))
  return (
    <section className="space-y-2 rounded-md border border-dashed p-3" aria-label="Suggested steps (AI)">
      <p className="flex items-center gap-1.5 text-xs font-medium">
        <Sparkles className="size-3.5" aria-hidden="true" />
        Suggested steps (AI, from the circular – check the official text)
      </p>
      <ol className="list-decimal space-y-2 pl-5 text-sm">
        {steps.map((step, index) => (
          <li key={index} className="space-y-1">
            <p>{step.text}</p>
            <p className="flex flex-wrap gap-1">
              {step.chunk_ids.map((chunkId) => (
                <button
                  key={chunkId}
                  type="button"
                  onClick={() => onCite(chunkId)}
                  className="rounded border px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
                  aria-label={`Show source ${byId[chunkId] ? sourceShortName(byId[chunkId]) : chunkId}`}
                >
                  Source: {byId[chunkId] ? sourceShortName(byId[chunkId]) : chunkId}
                </button>
              ))}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}
