import { ChevronDown } from "lucide-react"
import { Fragment } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { HORIZON_OPTIONS } from "../constants"
import { countFilled } from "../utils"
import { FeatureField } from "./FeatureField"

function FeatureSection({ group, values, setValue, descriptions, choices, invalid, defaultOpen, extraFields }) {
  const filled = countFilled(Object.fromEntries(group.features.map((name) => [name, values[name]])))

  return (
    <Collapsible defaultOpen={defaultOpen} className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm font-medium">{group.title}</p>
          <p className="text-xs text-muted-foreground">{group.description}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs tabular-nums text-muted-foreground">
            {filled} / {group.features.length}
          </span>
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-4 border-t p-4 sm:grid-cols-2 lg:grid-cols-3">
        {group.features.map((name) => (
          <Fragment key={name}>
            <FeatureField
              name={name}
              description={descriptions[name]}
              value={values[name] ?? ""}
              onChange={(value) => setValue(name, value)}
              choice={choices[name]}
              invalid={invalid.includes(name)}
            />
            {extraFields?.[name]}
          </Fragment>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function FeatureForm({
  groups,
  values,
  onChange,
  descriptions,
  choices,
  horizon,
  onHorizonChange,
  invalid = [],
  prefilledFromRiskCheck = false,
  extraFields,
  sections,
  advanced,
  waitingFor,
  onClear,
  onSubmit,
  pending,
}) {
  const total = groups.reduce((sum, group) => sum + group.features.length, 0)
  const setValue = (name, value) => onChange({ ...values, [name]: value })

  return (
    <Card>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit()
        }}
      >
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1.5">
              <CardTitle>Household features</CardTitle>
              <CardDescription>
                {countFilled(values)} of {total} filled. Blank numbers are sent
                as null and filled with the training median by the model. The 13
                market and macro values and the 14 history values are filled
                automatically.
              </CardDescription>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={onClear}>
              Clear
            </Button>
          </div>
          {prefilledFromRiskCheck && (
            <div>
              <Badge variant="outline">Prefilled from Risk Check (7 fields)</Badge>
            </div>
          )}
        </CardHeader>

        <CardContent className="space-y-3">
          {groups.map((group, index) => (
            <FeatureSection
              key={group.key}
              group={group}
              values={values}
              setValue={setValue}
              descriptions={descriptions}
              choices={choices}
              invalid={invalid}
              defaultOpen={index === 0}
              extraFields={extraFields}
            />
          ))}
          {sections}
          {advanced}
        </CardContent>

        <CardFooter className="flex-wrap justify-end gap-3">
          {invalid.length > 0 && (
            <p role="alert" className="mr-auto text-sm text-destructive">
              {invalid.length} field{invalid.length > 1 ? "s are" : " is"} not a
              number: {invalid.join(", ")}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Label htmlFor="risk-horizon" className="text-sm">
              Horizon
            </Label>
            <Select value={horizon} onValueChange={onHorizonChange}>
              <SelectTrigger id="risk-horizon" className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {HORIZON_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" disabled={pending || Boolean(waitingFor)}>
            {pending ? "Predicting…" : waitingFor || "Predict"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
