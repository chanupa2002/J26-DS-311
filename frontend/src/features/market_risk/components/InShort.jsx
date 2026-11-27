import { ListChecks } from "lucide-react"

import { NO_GUIDANCE_RULE } from "./v2format"

/** Lower-case the first letter unless the word looks like an acronym ("NVQ", "SDO"). */
function lowerFirst(text) {
  return /^[A-Z][a-z]/.test(text) ? text[0].toLowerCase() + text.slice(1) : text
}

function upperFirst(text) {
  return text ? text[0].toUpperCase() + text.slice(1) : text
}

/** "a", "a and b", "a, b and c" – or "a, x; b; c" when a part has its own comma. */
function joinNaturally(parts) {
  if (parts.length <= 1) return parts.join("")
  if (parts.some((part) => part.includes(","))) return parts.join("; ")
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`
}

function unique(values) {
  const seen = new Set()
  return values.filter((value) => {
    const key = value.trim().toLowerCase()
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

/** Situation sentence from the follow-up reason and the actions' reasons (Z1 has its own line). */
function situationText(followUp, actions) {
  const reasons = unique([followUp?.reason_label, ...actions.map((item) => item.reason_label)].filter(Boolean))
  if (!reasons.length) return ""
  const sentence = upperFirst(joinNaturally(reasons.map((reason, index) => (index ? lowerFirst(reason) : reason))))
  return /[.!?]$/.test(sentence) ? sentence : `${sentence}.`
}

/** "In short": a plain summary built only from the API fields – no AI. */
export function InShort({ followUp, actions }) {
  if (!followUp) return null
  const others = actions.filter((item) => item.rule_id !== NO_GUIDANCE_RULE)
  const noGuidance = actions.find((item) => item.rule_id === NO_GUIDANCE_RULE)
  const unguided = noGuidance ? Math.max(noGuidance.related_factors.length, 1) : 0
  const also = unique(others.map((item) => item.action_category))
  return (
    <section aria-labelledby="in-short-title" className="space-y-1.5 rounded-md bg-muted/60 p-3 text-sm">
      <h3 id="in-short-title" className="flex items-center gap-1.5 font-semibold">
        <ListChecks className="size-4" aria-hidden="true" />
        In short
      </h3>
      <p>{situationText(followUp, others)}</p>
      <p>
        <span className="font-medium">Main step: </span>
        {followUp.action_category} – {followUp.action_en}
      </p>
      {also.length > 0 && (
        <p>
          <span className="font-medium">Also: </span>
          {also.join(" · ")}
        </p>
      )}
      {unguided > 0 && (
        <p>
          {unguided} {unguided === 1 ? "reason has" : "reasons have"} no official guidance
        </p>
      )}
    </section>
  )
}
