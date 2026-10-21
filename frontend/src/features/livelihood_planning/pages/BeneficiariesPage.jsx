import { Search } from "lucide-react"
import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { PageState } from "../components/PageState"
import { useBeneficiaries } from "../hooks/useBeneficiaries"
import { displayValue } from "../utils"

export function BeneficiariesPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const beneficiaries = useBeneficiaries()
  const rows = useMemo(() => beneficiaries.data || [], [beneficiaries.data])
  const filteredRows = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("en")
    if (!term) return rows
    return rows.filter((beneficiary) =>
      [beneficiary.id, beneficiary.district].some((value) =>
        String(value || "")
          .toLocaleLowerCase("en")
          .includes(term),
      ),
    )
  }, [rows, search])

  if (beneficiaries.isPending) return <PageState loading />
  if (beneficiaries.isError) {
    return (
      <PageState
        error={beneficiaries.error}
        onRetry={() => beneficiaries.refetch()}
      />
    )
  }
  if (!rows.length) {
    return <PageState empty emptyMessage="No beneficiaries found." />
  }

  return (
    <div className="space-y-5">
      <div className="relative max-w-sm">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by ID or district"
          aria-label="Search beneficiaries by ID or district"
          className="pl-9"
        />
      </div>

      {filteredRows.length ? (
        <div className="rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Age</TableHead>
                <TableHead>Gender</TableHead>
                <TableHead>District</TableHead>
                <TableHead>Female-headed</TableHead>
                <TableHead>Disability</TableHead>
                <TableHead>Aswesuma category</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRows.map((beneficiary) => {
                return (
                  <TableRow key={beneficiary.id}>
                    <TableCell>
                      <div className="flex items-center gap-2 font-medium">
                        {beneficiary.id}
                        {beneficiary.is_demo === true && (
                          <Badge variant="secondary">Demo</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{displayValue(beneficiary.age)}</TableCell>
                    <TableCell>{displayValue(beneficiary.gender)}</TableCell>
                    <TableCell>{displayValue(beneficiary.district)}</TableCell>
                    <TableCell>
                      {displayValue(beneficiary.female_headed)}
                    </TableCell>
                    <TableCell>
                      {displayValue(beneficiary.disability)}
                    </TableCell>
                    <TableCell>
                      {displayValue(beneficiary.aswesuma_category)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() =>
                          navigate(`/livelihood/assess/${beneficiary.id}`)
                        }
                      >
                        Assess
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <PageState empty emptyMessage="No beneficiaries match your search." />
      )}
    </div>
  )
}
