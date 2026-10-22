export const LIVELIHOOD_CATEGORIES = [
  "AGRICULTURE & PLANTATION CROPS",
  "LIVESTOCK & ANIMAL HUSBANDRY",
  "FOOD PROCESSING & PRODUCTION",
  "TRADE",
  "GARMENT TEXTILE, HANDICRAFTS",
  "CONSTRUCTION, BUILDING AND REPAIR",
  "TRANSPORT & LOGISTICS",
  "BEAUTY AND WELLNESS",
]

export const PROBLEMS = [
  ["problem_sales_low", "Sales are low"],
  ["problem_asset_lost", "Asset was lost"],
  ["problem_input_cost", "Input costs are high"],
  ["problem_input_unavailable", "Inputs are unavailable"],
  ["problem_storage_transport", "Storage or transport problem"],
  ["problem_equipment", "Equipment problem"],
  ["problem_disaster", "Disaster impact"],
]

export const initialForm = {
  household_id: "",
  year: String(new Date().getFullYear()),
  month_number: String(new Date().getMonth() + 1),
  livelihood_category: "",
  grant_amount_lkr: "",
  monthly_expenditure_lkr: "",
  grant_use_status: "",
  grant_used_per_plan: "",
  disaster_impact_reported: "",
  livelihood_difficulty_reported: "",
  business_running: "",
  profit: "",
  borrowed_money: "",
  revenue_mid_lkr: "",
  record_keeping_level: "",
  saved_amount_lkr: "",
}
