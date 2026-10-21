import { toast } from "sonner"

import { API_URL } from "@/lib/env"

function readableDetail(detail, fallback) {
  if (typeof detail === "string" && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg).filter(Boolean)
    if (messages.length) return messages.join(" ")
  }
  return fallback
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  try {
    const response = await fetch(`${API_URL}${path}`, { ...options, headers })
    const isJson = response.headers
      .get("content-type")
      ?.includes("application/json")
    const body = isJson ? await response.json() : await response.text()

    if (!response.ok) {
      throw new Error(
        readableDetail(
          body?.detail,
          `Request failed with status ${response.status}.`,
        ),
      )
    }
    return body
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "The request could not be completed."
    toast.error(message)
    throw error instanceof Error ? error : new Error(message)
  }
}
