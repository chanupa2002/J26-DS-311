import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const EMPTY_VALUE = "__none__"

export function BeneficiarySelect({ beneficiaries, value, onChange }) {
  return (
    <div className="max-w-xl space-y-2">
      <Label htmlFor="beneficiary-select">Beneficiary</Label>
      <Select
        value={value ? String(value) : EMPTY_VALUE}
        onValueChange={(nextValue) =>
          onChange(nextValue === EMPTY_VALUE ? "" : nextValue)
        }
      >
        <SelectTrigger id="beneficiary-select">
          <SelectValue placeholder="Select a beneficiary" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={EMPTY_VALUE}>Select a beneficiary</SelectItem>
          {beneficiaries.map((beneficiary) => (
            <SelectItem key={beneficiary.id} value={String(beneficiary.id)}>
              {beneficiary.id} · {beneficiary.full_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
