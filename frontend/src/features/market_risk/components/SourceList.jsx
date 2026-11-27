import { ChevronDown, ExternalLink, FileText, TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { dayText, hasSinhala, sourceAnchor } from "./v2format"

// System fonts only (no new package): readable Sinhala on Windows, macOS, Android and Linux.
const SINHALA_FONTS = '"Noto Sans Sinhala", "Iskoola Pota", "Sinhala Sangam MN", "Sinhala MN", "Nirmala UI", sans-serif'

function OriginalText({ text, sinhala }) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">Original circular text (OCR – may contain reading errors)</p>
      <p
        lang={sinhala ? "si" : "en"}
        className="whitespace-pre-line break-words text-sm leading-relaxed"
        style={sinhala ? { fontFamily: SINHALA_FONTS } : undefined}
      >
        {text}
      </p>
    </div>
  )
}

/** Sinhala source with a machine translation: English tab first, the original one click away. */
function TranslatedText({ source }) {
  return (
    <Tabs defaultValue="en">
      <TabsList aria-label="Language of the passage" className="h-auto flex-wrap">
        <TabsTrigger value="en" className="whitespace-normal">
          English (machine translation)
        </TabsTrigger>
        <TabsTrigger value="si" className="whitespace-normal">
          Sinhala (original)
        </TabsTrigger>
      </TabsList>
      <TabsContent value="en" className="space-y-1">
        <p className="text-xs text-muted-foreground">Machine translation – check the original</p>
        <p lang="en" className="whitespace-pre-line break-words text-sm leading-relaxed">
          {source.excerpt_en}
        </p>
      </TabsContent>
      <TabsContent value="si">
        <OriginalText text={source.excerpt} sinhala />
      </TabsContent>
    </Tabs>
  )
}

function SourceItem({ source, scope, open, onToggle }) {
  const anchor = sourceAnchor(scope, source.chunk_id)
  const textId = `${anchor}-text`
  const sinhala = hasSinhala(source.excerpt)
  const note = String(source.status_note || "").trim()
  const warn = note && note.toLowerCase() !== "current"
  return (
    <li id={anchor} tabIndex={-1} className="space-y-2 rounded-md border p-3 text-sm focus-visible:outline-2 focus-visible:outline-ring">
      <p className="flex gap-2">
        <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="min-w-0 break-words">
          {[source.circular_no, source.title_en, source.page ? `page ${source.page}` : null, dayText(source.date)]
            .filter(Boolean)
            .join(" · ")}
        </span>
      </p>
      {warn && (
        <p className="flex gap-2 text-xs font-medium text-amber-800 dark:text-amber-300">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>Check: {note}</span>
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" size="sm" aria-expanded={open} aria-controls={textId} onClick={onToggle}>
          <ChevronDown className={`size-4 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
          {open ? "Hide official text" : "Show official text"}
        </Button>
        {source.source_url && (
          <Button asChild variant="ghost" size="sm">
            <a href={source.source_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-4" aria-hidden="true" />
              Open circular (PDF)
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </Button>
        )}
      </div>
      {open && (
        <div id={textId} className="rounded-md bg-muted/60 p-3">
          {sinhala && source.excerpt_en ? (
            <TranslatedText source={source} />
          ) : (
            <OriginalText text={source.excerpt} sinhala={sinhala} />
          )}
        </div>
      )}
    </li>
  )
}

/** Official circular passages for one suggestion. `openIds` / `onToggle` come from the parent. */
export function SourceList({ sources = [], scope, openIds, onToggle }) {
  if (!sources.length) return null
  return (
    <section className="space-y-2" aria-label="Official sources">
      <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Official sources</h4>
      <ul className="space-y-2">
        {sources.map((source) => (
          <SourceItem
            key={source.chunk_id}
            source={source}
            scope={scope}
            open={openIds.has(source.chunk_id)}
            onToggle={() => onToggle(source.chunk_id)}
          />
        ))}
      </ul>
    </section>
  )
}
