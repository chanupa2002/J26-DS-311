import { api } from "@/lib/api"

export const beneficiaryApi = {
  geography: () => api("/geography", { cache: "no-store" }),
  glossary: () => api("/glossary", { cache: "no-store" }),
  derive: (answers) => api("/assess/derive", { method: "POST", body: JSON.stringify(answers) }),
  assess: (answers) => api("/assess/score", { method: "POST", body: JSON.stringify(answers) }),
  households: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value !== "" && value != null),
    )
    return api(`/households?${query}`)
  },
  stage6Rankings: (params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== "" && value != null))
    return api(`/stage6/rankings?${query}`, { cache: "no-store" })
  },
  household: (rowId) => api(`/households/${rowId}`),
  summary: () => api("/summary", { cache: "no-store" }),
  sensitivity: () => api("/sensitivity"),
  modelInfo: () => api("/model-info"),
  spec: () => api("/spec"),
  score: (leaves) => api("/whatif", { method: "POST", body: JSON.stringify({ leaves }) }),
}
