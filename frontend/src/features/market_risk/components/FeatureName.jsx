import { featureLabel } from "../utils"

/** A feature's short label; the F_* name (and an optional description) is in the tooltip. */
export function FeatureName({ name, description, className }) {
  return (
    <span className={className} title={description ? `${description} (${name})` : name}>
      {featureLabel(name)}
    </span>
  )
}
