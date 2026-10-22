import { API_URL } from "@/lib/env"

const FINANCIAL_PATH = "/evidence-trust/financial"

export async function submitMonitoring(form) {
  const body = new FormData()
  Object.entries(form).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return
    if (key === "bills") {
      value.forEach((file) => body.append("bills", file))
    } else if (key === "image") {
      body.append("image", value)
    } else {
      body.append(key, String(value))
    }
  })

  const response = await fetch(`${API_URL}${FINANCIAL_PATH}/monitoring`, {
    method: "POST",
    body,
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg).join(" ")
      : payload.detail
    throw new Error(detail || "The monitoring record could not be submitted.")
  }
  return payload
}

export async function getMonitoringRecords() {
  const response = await fetch(`${API_URL}${FINANCIAL_PATH}/monitoring`)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || "Could not load monitoring records.")
  return payload.records || []
}
