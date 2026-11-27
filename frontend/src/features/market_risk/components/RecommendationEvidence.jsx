import { CircleCheck, CircleX } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

function pagesText(cited) {
  const byDoc = new Map()
  for (const { doc_id: doc, page } of cited) {
    const name = doc || "page"
    byDoc.set(name, [...(byDoc.get(name) || []), page])
  }
  return [...byDoc].map(([doc, pages]) => `${doc} p. ${pages.join(", ")}`).join("; ")
}

function Figure({ label, value }) {
  return (
    <div className="rounded-md border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function MatchText({ matched }) {
  const Icon = matched ? CircleCheck : CircleX
  return (
    <span className={`inline-flex items-center gap-1 font-medium ${matched ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400"}`}>
      <Icon className="size-4" aria-hidden="true" />
      {matched ? "Match" : "Miss"}
    </span>
  )
}

/** "Recommendation engine (FR4–FR5)" on Model evidence. Every number comes from /model/evidence. */
export function RecommendationEvidence({ data }) {
  if (!data) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Recommendation engine (FR4–FR5)</CardTitle>
          <CardDescription>The knowledge base is not installed on this server.</CardDescription>
        </CardHeader>
      </Card>
    )
  }
  const retrieval = data.retrieval_check
  const pages = data.source_page_check
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Recommendation engine (FR4–FR5)</CardTitle>
        <CardDescription>
          Rule table plus search over official circulars. Version {data.knowledge_version}.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Figure label="Rules (validated / total)" value={`${data.n_rules_validated} / ${data.n_rules}`} />
          <Figure label="Official documents" value={data.n_documents} />
          <Figure label="Passages (chunks)" value={data.n_chunks} />
        </div>
        <div className="space-y-1">
          <p className="font-medium">
            Correct circular in top 1: {retrieval.hit_at_1} of {retrieval.queries} · top 3: {retrieval.hit_at_3} of{" "}
            {retrieval.queries}
          </p>
          <p className="text-xs text-muted-foreground">{retrieval.queries} test questions with known answers</p>
        </div>
        {data.translations && (
          <p>
            English translations: {data.translations.translated} of {data.translations.sinhala_chunks} Sinhala
            passages (machine translation)
            {data.translations.model && (
              <span className="text-xs text-muted-foreground"> · {data.translations.model}</span>
            )}
          </p>
        )}
        <div className="space-y-2">
          <p className="font-medium">
            Top passage from the cited page: {pages.matched} of {pages.total}
          </p>
          <p className="text-xs text-muted-foreground">
            Measures whether the system shows the exact page of the circular each rule cites.
          </p>
          <div className="-mx-6 sm:mx-0">
            <Table className="min-w-[560px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Cited document and page</TableHead>
                  <TableHead>Retrieved document and page</TableHead>
                  <TableHead>Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pages.rules.map((row) => (
                  <TableRow key={row.rule_id}>
                    <TableCell className="font-medium">{row.rule_id}</TableCell>
                    <TableCell className="text-xs">{pagesText(row.cited_pages)}</TableCell>
                    <TableCell className="text-xs">
                      {row.top_doc_id} p. {row.top_page ?? "—"}
                    </TableCell>
                    <TableCell>
                      <MatchText matched={row.matched} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
