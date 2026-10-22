import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { Link, useLocation } from "react-router-dom"

import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

const GlossaryContext = createContext({})
const LABEL = "Research output - not an eligibility determination"

export function ResearchPageFrame({ children }) {
  const [glossary, setGlossary] = useState({})
  const [metadata, setMetadata] = useState(null)
  const [service, setService] = useState(null)
  const [guideOpen, setGuideOpen] = useState(() => sessionStorage.getItem("c1-how-to-read-dismissed") !== "yes")

  useEffect(() => {
    api("/glossary").then((body) => setGlossary(Object.fromEntries((body.entries || []).map((entry) => [entry.id, entry])))).catch(() => setGlossary({}))
    api("/model-info").then(setMetadata).catch(() => setMetadata(null))
    api("/health").then(setService).catch(() => setService(null))
  }, [])

  const contextValue = useMemo(() => glossary, [glossary])
  return <GlossaryContext.Provider value={contextValue}>
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">{LABEL}</p>
      <Card>
        <CardHeader className="flex-row items-center justify-between gap-3"><CardTitle className="text-base">How to read this page</CardTitle><Button size="sm" variant="outline" aria-expanded={guideOpen} onClick={() => {
          const next = !guideOpen
          setGuideOpen(next)
          if (!next) sessionStorage.setItem("c1-how-to-read-dismissed", "yes")
        }}>{guideOpen ? "Collapse guidance" : "Show guidance"}</Button></CardHeader>
        {guideOpen && <CardContent className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2"><p><strong className="text-foreground">1. Check the comparison group.</strong> Percentiles describe position among a named set of saved records.</p><p><strong className="text-foreground">2. Check evidence used.</strong> Unknown inputs stay unknown; they are not No or zero.</p><p><strong className="text-foreground">3. Read probabilities together.</strong> Low, medium, and high can all have non-zero model probability.</p><p><strong className="text-foreground">4. Treat results as research output.</strong> The prototype is not validated for eligibility decisions.</p></CardContent>}
      </Card>
      {children}
      <footer className="flex flex-wrap gap-x-4 gap-y-1 border-t pt-3 text-xs text-muted-foreground" aria-label="Research model information">
        <span>Model {metadata?.model_version || "Unavailable"}</span>
        <span>Spec {metadata?.spec_version || "Unavailable"}</span>
        <span>Data {metadata?.data_manifest_sha256 ? metadata.data_manifest_sha256.slice(0, 10) : "Unavailable"}</span>
        <span>Service {service?.status || "Unavailable"}{service?.data_mode ? ` (${service.data_mode.toLowerCase()})` : ""}</span>
        <Link className="underline underline-offset-2" to="/beneficiary-selection/method#changelog">Changelog</Link>
      </footer>
    </div>
  </GlossaryContext.Provider>
}

export function GlossaryEntry({ id, showShort = false }) {
  const glossary = useContext(GlossaryContext)
  const entry = glossary[id]
  return <InfoPopover entry={entry} fallbackId={id} showShort={showShort} />
}

export function InfoPopover({ entry, fallbackId, showShort = false }) {
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState(false)
  const popoverId = `glossary-${entry?.id || fallbackId}`

  useEffect(() => {
    if (!open) return undefined
    const onKeyDown = (event) => { if (event.key === "Escape") setOpen(false) }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [open])

  function recordFeedback(answer) {
    const storageKey = "c1-glossary-feedback-v1"
    const prior = JSON.parse(localStorage.getItem(storageKey) || "[]")
    prior.push({ term_id: entry?.id || fallbackId, answer, timestamp: new Date().toISOString(), page: location.pathname })
    localStorage.setItem(storageKey, JSON.stringify(prior))
    setSaved(true)
  }

  return <span className="relative inline-flex items-center gap-1">
    {showShort && entry?.short && <span className="text-sm text-muted-foreground">{entry.short}</span>}
    <button type="button" className="inline-flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring" aria-label={`Explain ${entry?.plain_label || fallbackId}`} aria-expanded={open} aria-controls={popoverId} onClick={() => { setOpen(!open); setSaved(false) }}>i</button>
    {open && <section id={popoverId} role="dialog" aria-labelledby={`${popoverId}-title`} className="absolute left-0 top-8 z-50 w-72 rounded-lg border bg-popover p-3 text-popover-foreground shadow-lg">
      <h3 id={`${popoverId}-title`} className="font-semibold">{entry?.plain_label || fallbackId}</h3>
      {entry?.technical_term && <p className="mt-1 text-xs text-muted-foreground">{entry.technical_term}</p>}
      <p className="mt-2 text-sm">{entry?.popover || "TODO: definition needs review."}</p>
      {entry?.method_text?.startsWith("TODO:") && <p className="mt-2 text-xs font-medium">{entry.method_text}</p>}
      <div className="mt-3 border-t pt-2" aria-live="polite"><p className="text-xs">Was this clear?</p>{saved ? <p className="mt-1 text-xs text-muted-foreground">Thanks for the feedback.</p> : <div className="mt-1 flex gap-2"><button className="rounded border px-2 py-1 text-xs focus-visible:outline-2 focus-visible:outline-ring" onClick={() => recordFeedback("yes")}>Yes</button><button className="rounded border px-2 py-1 text-xs focus-visible:outline-2 focus-visible:outline-ring" onClick={() => recordFeedback("no")}>No</button></div>}</div>
    </section>}
  </span>
}

export function HowToReadPanel() {
  return <Card><CardHeader><CardTitle className="text-base">First visit guide</CardTitle></CardHeader><CardContent className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-2"><p>1. Choose a page based on whether you are exploring saved scores, testing inputs, or reviewing methods.</p><p>2. Check the comparison group and evidence used before interpreting any score.</p><p>3. Open the information buttons for plain-language definitions.</p><p>4. Review limitations and sensitivity results before drawing research conclusions.</p></CardContent></Card>
}
