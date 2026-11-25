import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm, useWatch } from "react-hook-form"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { FEATURE_OPTIONS } from "../constants"
import { categoryLabel } from "./v2format"

// Select values are strings. NONE = not answered (null); DK = "Don't know" (null + *_dk flag).
const NONE = "none"
const DK = "dk"
const YES_NO = [
  { value: "1", label: "Yes" },
  { value: "0", label: "No" },
]
const UNKNOWN = { value: NONE, label: "Don't know / not answered" }
const NOT_ANSWERED = { value: NONE, label: "Not answered" }
const DONT_KNOW = { value: DK, label: "Don't know" }
const BANDS = ["lowest", "low", "high", "highest"].map((word, band) => ({ value: String(band), label: `Band ${band} (${word})` }))
// Codebook labels already used by the v1 page (frontend constants of this feature).
const fromV1 = (feature) => FEATURE_OPTIONS[feature].options

const ANSWERS = [
  { section: "Business this month" },
  { name: "business_running", label: "Is the business running?", options: [...YES_NO, UNKNOWN] },
  { name: "profit", label: "Did the business make a profit last month?", options: [...YES_NO, DONT_KNOW, NOT_ANSWERED], dk: "profit_dk" },
  { name: "coach_progressing", label: "Coach: is the business progressing well?", options: [...YES_NO, DONT_KNOW, NOT_ANSWERED], dk: "coach_progressing_dk" },
  { name: "revenue_band", label: "Revenue band last month", options: [...BANDS, DONT_KNOW, NOT_ANSWERED], dk: "revenue_band_dk" },
  { name: "hours_band", label: "Hours worked in the business", options: [...fromV1("F_Hours_Ord_t"), UNKNOWN] },
  { name: "record_keeping", label: "How often are business records kept?", options: [...fromV1("F_Records_Ord_t"), DONT_KNOW, NOT_ANSWERED], dk: "record_keeping_dk" },
  { section: "Money and grant" },
  { name: "borrowed_money", label: "Borrowed money this month?", options: [...YES_NO, UNKNOWN] },
  { name: "saved_money", label: "Saved money this month?", options: [...YES_NO, UNKNOWN] },
  { name: "grant_status", label: "Samurdhi grant status", options: [...fromV1("F_Grant_Status_Ord_t"), UNKNOWN] },
  { section: "Problems this month" },
  { name: "problem_sales_low", label: "Sales were low", options: [...YES_NO, UNKNOWN] },
  { name: "problem_input_cost", label: "Input costs were too high", options: [...YES_NO, UNKNOWN] },
  { name: "problem_input_unavailable", label: "Inputs were not available", options: [...YES_NO, UNKNOWN] },
  { name: "problem_asset_lost", label: "A business asset was lost", options: [...YES_NO, UNKNOWN] },
  { name: "problem_storage_transport", label: "Storage or transport problem", options: [...YES_NO, UNKNOWN] },
  { name: "problem_equipment", label: "Equipment or machinery problem", options: [...YES_NO, UNKNOWN] },
  { name: "problem_disaster", label: "Natural disaster", options: [...YES_NO, UNKNOWN] },
]
const ANSWER_FIELDS = ANSWERS.filter((item) => item.name)
const NOT_APPLICABLE = [
  { name: "children_in_school_not_applicable", label: "Children in school: not applicable (no school-age children)" },
  { name: "ill_member_got_care_not_applicable", label: "Ill member got care: not applicable (no one was ill)" },
  { name: "referral_reached_not_applicable", label: "Referral reached: not applicable (no referral)" },
]

const EMPTY = {
  mode: "synthetic",
  household_key: "",
  first_visit: false,
  monitoring_period: "",
  district: "",
  category: "",
  ...Object.fromEntries(ANSWER_FIELDS.map(({ name }) => [name, NONE])),
  ...Object.fromEntries(NOT_APPLICABLE.map(({ name }) => [name, false])),
}

// The synthetic example of the API contract (SIM-HH-001, 2026-06, Ampara, Agriculture).
const EXAMPLE = {
  ...EMPTY,
  household_key: "SIM-HH-001",
  monitoring_period: "2026-06",
  district: "Ampara",
  category: "AGRICULTURE & PLANTATION CROPS",
  business_running: "1",
  profit: "0",
  coach_progressing: "1",
  revenue_band: "1",
  hours_band: "2",
  record_keeping: "1",
  borrowed_money: "0",
  saved_money: "0",
  grant_status: "3",
  problem_sales_low: "1",
  problem_input_cost: "0",
  problem_input_unavailable: "0",
}

const schema = z
  .object({
    mode: z.enum(["synthetic", "real"]),
    household_key: z.string().trim(),
    first_visit: z.boolean(),
    monitoring_period: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/, "Choose the visit month."),
    district: z.string().min(1, "Choose a district."),
    category: z.string().min(1, "Choose a livelihood."),
  })
  .loose()
  .superRefine((values, ctx) => {
    if (values.mode === "synthetic" && !/^SIM-HH-[A-Za-z0-9-]+$/.test(values.household_key)) {
      ctx.addIssue({ code: "custom", path: ["household_key"], message: "Enter a simulated household key, e.g. SIM-HH-001." })
    }
  })

/** Form values -> VisitRequest body (exactly the fields of v2/schemas.py). */
function toRequest(values) {
  const synthetic = values.mode === "synthetic"
  const body = {
    monitoring_period: values.monitoring_period,
    district: values.district,
    category: values.category,
    is_synthetic: synthetic,
  }
  if (synthetic) {
    body.household_key = values.household_key.trim()
    if (values.first_visit) body.previous_visits = []
  }
  for (const { name, dk } of ANSWER_FIELDS) {
    const value = values[name]
    body[name] = value === NONE || value === DK ? null : Number(value)
    if (dk) body[dk] = value === DK ? 1 : 0
  }
  for (const { name } of NOT_APPLICABLE) body[name] = values[name] ? 1 : 0
  return body
}

function FieldError({ id, message }) {
  if (!message) return null
  return (
    <p id={id} className="text-xs text-destructive">
      {message}
    </p>
  )
}

function SelectField({ control, name, label, options, placeholder = "Choose…", error }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={name}>{label}</Label>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <Select value={field.value || undefined} onValueChange={field.onChange}>
            <SelectTrigger id={name} aria-invalid={Boolean(error)} aria-describedby={error ? `${name}-error` : undefined}>
              <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />
      <FieldError id={`${name}-error`} message={error} />
    </div>
  )
}

/** One monitoring visit. Districts and livelihoods come from the market table of the API. */
export function VisitForm({ districts = [], categories = [], onSubmit, submitting }) {
  const { control, register, handleSubmit, reset, formState } = useForm({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })
  const mode = useWatch({ control, name: "mode" })
  const errors = formState.errors
  const synthetic = mode === "synthetic"

  return (
    <form onSubmit={handleSubmit((values) => onSubmit(toRequest(values)))} noValidate>
      <Card>
        <CardHeader className="flex flex-col gap-3 pb-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">Visit form</CardTitle>
            <CardDescription>Nothing is stored. Blank answers are sent as not answered.</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => reset(EXAMPLE)}>
              Fill simulated example
            </Button>
            <Button type="button" variant="ghost" onClick={() => reset(EMPTY)}>
              Clear
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <legend className="mb-2 text-sm font-medium">Visit</legend>
            <SelectField
              control={control}
              name="mode"
              label="Household type"
              options={[
                { value: "synthetic", label: "Simulated household (SIM-HH-…)" },
                { value: "real", label: "Real visit (no key, no history)" },
              ]}
            />
            {synthetic && (
              <div className="space-y-1.5">
                <Label htmlFor="household_key">Simulated household key</Label>
                <Input
                  id="household_key"
                  placeholder="SIM-HH-001"
                  aria-invalid={Boolean(errors.household_key)}
                  aria-describedby={errors.household_key ? "household_key-error" : undefined}
                  {...register("household_key")}
                />
                <FieldError id="household_key-error" message={errors.household_key?.message} />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="monitoring_period">Visit month</Label>
              <Input
                id="monitoring_period"
                type="month"
                aria-invalid={Boolean(errors.monitoring_period)}
                aria-describedby={errors.monitoring_period ? "monitoring_period-error" : undefined}
                {...register("monitoring_period")}
              />
              <FieldError id="monitoring_period-error" message={errors.monitoring_period?.message} />
            </div>
            <SelectField
              control={control}
              name="district"
              label="District"
              options={districts.map((district) => ({ value: district, label: district }))}
              error={errors.district?.message}
            />
            <SelectField
              control={control}
              name="category"
              label="Livelihood"
              options={categories.map((category) => ({ value: category, label: categoryLabel(category) }))}
              error={errors.category?.message}
            />
            {synthetic && (
              <label className="flex items-center gap-2 self-end pb-2 text-sm">
                <input type="checkbox" className="size-4 accent-primary" {...register("first_visit")} />
                First visit (ignore earlier stored visits)
              </label>
            )}
          </fieldset>

          {ANSWERS.reduce((groups, item) => {
            if (item.section) groups.push({ title: item.section, fields: [] })
            else groups[groups.length - 1].fields.push(item)
            return groups
          }, []).map((group) => (
            <fieldset key={group.title} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <legend className="mb-2 text-sm font-medium">{group.title}</legend>
              {group.fields.map((field) => (
                <SelectField key={field.name} control={control} name={field.name} label={field.label} options={field.options} />
              ))}
            </fieldset>
          ))}

          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Questions that do not apply</legend>
            {NOT_APPLICABLE.map((item) => (
              <label key={item.name} className="flex items-start gap-2 text-sm">
                <input type="checkbox" className="mt-0.5 size-4 accent-primary" {...register(item.name)} />
                {item.label}
              </label>
            ))}
          </fieldset>

          <Button type="submit" disabled={submitting}>
            {submitting ? "Checking…" : "Check this visit"}
          </Button>
        </CardContent>
      </Card>
    </form>
  )
}
