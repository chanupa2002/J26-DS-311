import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

import { cleanProfile } from "../utils"

const EMPTY_VALUE = "__none__"
const DISTRICTS = [
  "Ampara",
  "Anuradhapura",
  "Badulla",
  "Batticaloa",
  "Colombo",
  "Galle",
  "Gampaha",
  "Hambantota",
  "Jaffna",
  "Kalutara",
  "Kandy",
  "Kegalle",
  "Kilinochchi",
  "Kurunegala",
  "Mannar",
  "Matale",
  "Matara",
  "Monaragala",
  "Mullaitivu",
  "Nuwara Eliya",
  "Polonnaruwa",
  "Puttalam",
  "Ratnapura",
  "Trincomalee",
  "Vavuniya",
]
const GENDERS = ["Female", "Male"]
const ASWESUMA_CATEGORIES = ["Poor", "Severely Poor", "Vulnerable"]

const profileSchema = z.object({
  district: z.string().optional(),
  ds_division: z.string().optional(),
  age: z.preprocess(
    (value) => (value === "" ? undefined : Number(value)),
    z
      .number()
      .int()
      .min(0, "Age must be at least 0.")
      .max(120, "Age must be 120 or less.")
      .optional(),
  ),
  gender: z.string().optional(),
  female_headed: z.boolean().optional(),
  disability: z.boolean().optional(),
  aswesuma_category: z.string().optional(),
  track: z.string().optional(),
})

function SelectField({ control, name, label, options }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <Select
            value={field.value || EMPTY_VALUE}
            onValueChange={(value) =>
              field.onChange(value === EMPTY_VALUE ? "" : value)
            }
          >
            <SelectTrigger id={name} onBlur={field.onBlur}>
              <SelectValue placeholder="Not provided" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={EMPTY_VALUE}>Not provided</SelectItem>
              {options.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />
    </div>
  )
}

function SwitchField({ control, name, label }) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
          <Label htmlFor={name}>{label}</Label>
          <button
            id={name}
            type="button"
            role="switch"
            aria-checked={field.value}
            onBlur={field.onBlur}
            onClick={() => field.onChange(!field.value)}
            className={cn(
              "relative h-6 w-11 shrink-0 rounded-full border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              field.value ? "bg-primary" : "bg-muted",
            )}
          >
            <span
              className={cn(
                "block size-5 rounded-full bg-background shadow-sm transition-transform",
                field.value ? "translate-x-5" : "translate-x-0",
              )}
            />
          </button>
        </div>
      )}
    />
  )
}

export function ProfileForm({ onSubmit, submitting = false, submitLabel }) {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      district: "",
      ds_division: "",
      age: "",
      gender: "",
      female_headed: false,
      disability: false,
      aswesuma_category: "",
      track: "",
    },
  })

  return (
    <Card>
      <form onSubmit={handleSubmit((values) => onSubmit(cleanProfile(values)))}>
        <CardContent className="grid gap-5 pt-6 md:grid-cols-2">
          <SelectField
            control={control}
            name="district"
            label="District"
            options={DISTRICTS}
          />
          <div className="space-y-2">
            <Label htmlFor="ds_division">DS division</Label>
            <Input id="ds_division" {...register("ds_division")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="age">Age</Label>
            <Input
              id="age"
              type="number"
              min="0"
              max="120"
              {...register("age")}
            />
            {errors.age && (
              <p className="text-sm text-destructive">{errors.age.message}</p>
            )}
          </div>
          <SelectField
            control={control}
            name="gender"
            label="Gender"
            options={GENDERS}
          />
          <SwitchField
            control={control}
            name="female_headed"
            label="Female-headed household"
          />
          <SwitchField
            control={control}
            name="disability"
            label="Household member with a disability"
          />
          <SelectField
            control={control}
            name="aswesuma_category"
            label="Aswesuma category"
            options={ASWESUMA_CATEGORIES}
          />
          <div className="space-y-2">
            <Label htmlFor="track">Track</Label>
            <Input id="track" {...register("track")} />
          </div>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Processing…" : submitLabel}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
