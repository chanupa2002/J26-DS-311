import { Check } from "lucide-react"

import { DECISION_LABELS, NO_GUIDANCE_RULE } from "./v2format"

function actionText(item) {
  // Z1's category already says "No official guidance found", so the line ends "– refer to the officer".
  return item.rule_id === NO_GUIDANCE_RULE ? "refer to the officer" : item.action_en
}

/**
 * "Plan for this household": one line per suggestion (follow-up first, then the cards in order).
 * Each line links to its card's title id; `onJump(titleId)` opens hidden cards and moves focus there.
 */
export function PlanList({ followUp, actions, onJump }) {
  const items = [
    ...(followUp ? [{ item: followUp, titleId: "follow-up-title" }] : []),
    ...actions.map((item) => ({ item, titleId: `action-${item.rule_id}-title` })),
  ]
  if (!items.length) return null
  return (
    <nav aria-labelledby="plan-title" className="rounded-md border p-3">
      <h3 id="plan-title" className="mb-2 text-sm font-semibold">
        Plan for this household
      </h3>
      <ol className="space-y-1.5 text-sm">
        {items.map(({ item, titleId }, index) => (
          <li key={item.rule_id} className="flex gap-2">
            <span className="w-5 shrink-0 text-right text-muted-foreground">{index + 1}.</span>
            <a
              href={`#${titleId}`}
              onClick={(event) => {
                event.preventDefault()
                onJump(titleId)
              }}
              className="min-w-0 flex-1 break-words rounded underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
            >
              <span className="font-medium">{item.action_category}</span>
              {" – "}
              {actionText(item)}
            </a>
            {item.decision && (
              <span className="flex shrink-0 items-start gap-1 text-xs text-muted-foreground">
                <Check className="mt-0.5 size-4 text-foreground" aria-hidden="true" />
                <span className="sr-only">
                  Decision saved: {DECISION_LABELS[item.decision.decision] || item.decision.decision}
                </span>
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
