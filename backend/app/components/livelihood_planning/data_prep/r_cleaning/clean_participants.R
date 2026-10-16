library(readxl)
library(dplyr)
library(stringr)
library(readr)
library(tibble)

input_file <- "//Enter your file path//"
out_dir <- "cleaned_data"
dir.create(out_dir, showWarnings = FALSE)

sheets <- c("Ampara", "Badulla", "Monaragala")
n_real <- 199

categories <- c(
  "AGRICULTURE & PLANTATION CROPS", "LIVESTOCK & ANIMAL HUSBANDRY",
  "FOOD PROCESSING & PRODUCTION", "TRADE", "GARMENT TEXTILE, HANDICRAFTS",
  "CONSTRUCTION, BUILDING AND REPAIR", "TRANSPORT & LOGISTICS",
  "BEAUTY AND WELLNESS", "OTHER"
)

livelihood_map <- tribble(
  ~key, ~category,
  "banana cultivation", "AGRICULTURE & PLANTATION CROPS",
  "chilli cultivation", "AGRICULTURE & PLANTATION CROPS",
  "cinnamon cultivation", "AGRICULTURE & PLANTATION CROPS",
  "cultivation of orange & lime", "AGRICULTURE & PLANTATION CROPS",
  "gardening", "AGRICULTURE & PLANTATION CROPS",
  "ginger cultivation", "AGRICULTURE & PLANTATION CROPS",
  "home garden", "AGRICULTURE & PLANTATION CROPS",
  "lime cultivation", "AGRICULTURE & PLANTATION CROPS",
  "mushroom cultivation", "AGRICULTURE & PLANTATION CROPS",
  "papaya cultivation", "AGRICULTURE & PLANTATION CROPS",
  "pepper cultivation", "AGRICULTURE & PLANTATION CROPS",
  "tea cultivation", "AGRICULTURE & PLANTATION CROPS",
  "vegetable cultivation", "AGRICULTURE & PLANTATION CROPS",
  "barber shop", "BEAUTY AND WELLNESS",
  "beauty salon", "BEAUTY AND WELLNESS",
  "bridal dressing", "BEAUTY AND WELLNESS",
  "gents salon", "BEAUTY AND WELLNESS",
  "hair dressing", "BEAUTY AND WELLNESS",
  "home beauty services", "BEAUTY AND WELLNESS",
  "home eauty services", "BEAUTY AND WELLNESS",
  "ladies beauty parlour", "BEAUTY AND WELLNESS",
  "saree darping and dressing", "BEAUTY AND WELLNESS",
  "saree draping and dressing", "BEAUTY AND WELLNESS",
  "block stone industry", "CONSTRUCTION, BUILDING AND REPAIR",
  "brick industry", "CONSTRUCTION, BUILDING AND REPAIR",
  "brick making", "CONSTRUCTION, BUILDING AND REPAIR",
  "carpentry", "CONSTRUCTION, BUILDING AND REPAIR",
  "carpentry (home funitures)", "CONSTRUCTION, BUILDING AND REPAIR",
  "improving the welding workplace", "CONSTRUCTION, BUILDING AND REPAIR",
  "production of bollocks", "CONSTRUCTION, BUILDING AND REPAIR",
  "welding industry", "CONSTRUCTION, BUILDING AND REPAIR",
  "bread and bun making", "FOOD PROCESSING & PRODUCTION",
  "cake bites production", "FOOD PROCESSING & PRODUCTION",
  "cake makng", "FOOD PROCESSING & PRODUCTION",
  "catering service", "FOOD PROCESSING & PRODUCTION",
  "curry powder grinding", "FOOD PROCESSING & PRODUCTION",
  "curry powder production", "FOOD PROCESSING & PRODUCTION",
  "food packet catering", "FOOD PROCESSING & PRODUCTION",
  "food packett catering", "FOOD PROCESSING & PRODUCTION",
  "food production and sales", "FOOD PROCESSING & PRODUCTION",
  "food service", "FOOD PROCESSING & PRODUCTION",
  "grain grinding", "FOOD PROCESSING & PRODUCTION",
  "ice cream production", "FOOD PROCESSING & PRODUCTION",
  "ice cream retail trade", "FOOD PROCESSING & PRODUCTION",
  "ice cream/youghurt retail trade", "FOOD PROCESSING & PRODUCTION",
  "jaggery producton", "FOOD PROCESSING & PRODUCTION",
  "lamp poweder producation", "FOOD PROCESSING & PRODUCTION",
  "murukku and sweetmeat production", "FOOD PROCESSING & PRODUCTION",
  "pickle and chutney aking", "FOOD PROCESSING & PRODUCTION",
  "short eats and bakery items", "FOOD PROCESSING & PRODUCTION",
  "snack production", "FOOD PROCESSING & PRODUCTION",
  "spice grinding", "FOOD PROCESSING & PRODUCTION",
  "clay pottery", "GARMENT TEXTILE, HANDICRAFTS",
  "curtain production", "GARMENT TEXTILE, HANDICRAFTS",
  "decorative flower production", "GARMENT TEXTILE, HANDICRAFTS",
  "event ornaments suppliers", "GARMENT TEXTILE, HANDICRAFTS",
  "mat weaving", "GARMENT TEXTILE, HANDICRAFTS",
  "preparing coir brushes", "GARMENT TEXTILE, HANDICRAFTS",
  "ready - made clothing trade", "GARMENT TEXTILE, HANDICRAFTS",
  "ready-made clothing trade", "GARMENT TEXTILE, HANDICRAFTS",
  "sewing and readymade garment industry", "GARMENT TEXTILE, HANDICRAFTS",
  "sewing and readymode garment industry", "GARMENT TEXTILE, HANDICRAFTS",
  "sewing andredymadegarmentindustry", "GARMENT TEXTILE, HANDICRAFTS",
  "sewing industry", "GARMENT TEXTILE, HANDICRAFTS",
  "tailoring", "GARMENT TEXTILE, HANDICRAFTS",
  "weaving industry", "GARMENT TEXTILE, HANDICRAFTS",
  "broiler chicken farming", "LIVESTOCK & ANIMAL HUSBANDRY",
  "chicken faming-for eggs", "LIVESTOCK & ANIMAL HUSBANDRY",
  "chicken farming (eggs)", "LIVESTOCK & ANIMAL HUSBANDRY",
  "chicken farming (for meat)", "LIVESTOCK & ANIMAL HUSBANDRY",
  "chicken farming for eggs", "LIVESTOCK & ANIMAL HUSBANDRY",
  "ckicken control", "LIVESTOCK & ANIMAL HUSBANDRY",
  "dairy cattle farming", "LIVESTOCK & ANIMAL HUSBANDRY",
  "dairy farming", "LIVESTOCK & ANIMAL HUSBANDRY",
  "egg production farming", "LIVESTOCK & ANIMAL HUSBANDRY",
  "farm chicken farming (for eggs)", "LIVESTOCK & ANIMAL HUSBANDRY",
  "goad management", "LIVESTOCK & ANIMAL HUSBANDRY",
  "goat farming", "LIVESTOCK & ANIMAL HUSBANDRY",
  "goat rearing", "LIVESTOCK & ANIMAL HUSBANDRY",
  "poultry farming (layer)", "LIVESTOCK & ANIMAL HUSBANDRY",
  "poultry management", "LIVESTOCK & ANIMAL HUSBANDRY",
  "bicycle repair", "OTHER",
  "electrical repair services", "OTHER",
  "exercise book production", "OTHER",
  "fisheries", "OTHER",
  "freshwater fishing industry", "OTHER",
  "lake fishing", "OTHER",
  "mobile elctrical or electronic repair services", "OTHER",
  "mobile electrical or electronic repair services", "OTHER",
  "mobile phone repair", "OTHER",
  "motorcycle repair", "OTHER",
  "multi-plug production", "OTHER",
  "restaurants", "OTHER",
  "starting an ayurvedic dispensary", "OTHER",
  "tea shop", "OTHER",
  "tea shop and retail sales", "OTHER",
  "vehicle repair", "OTHER",
  "bookstore", "TRADE",
  "cocount palm trading", "TRADE",
  "fish trade", "TRADE",
  "fish trading", "TRADE",
  "grocery sales", "TRADE",
  "maintaining retail merchandise", "TRADE",
  "mobile trading", "TRADE",
  "ornamental goods shop", "TRADE",
  "peanuts and nuts for sale", "TRADE",
  "retail shop", "TRADE",
  "retail trade", "TRADE",
  "running a sales outlet", "TRADE",
  "sale of decorative iteam at the weekly market", "TRADE",
  "shoe sales", "TRADE",
  "spice trade", "TRADE",
  "vegetable market", "TRADE",
  "vegetable sales", "TRADE",
  "vegetable sales at the weekly market", "TRADE",
  "vegetable trading", "TRADE",
  "delivery service", "TRANSPORT & LOGISTICS",
  "goods transport (lorry)", "TRANSPORT & LOGISTICS",
  "motorcycle taxi", "TRANSPORT & LOGISTICS",
  "school van service", "TRANSPORT & LOGISTICS",
  "three-wheeler hire", "TRANSPORT & LOGISTICS",
  "tractor hire", "TRANSPORT & LOGISTICS",
  "tuk tuk hire", "TRANSPORT & LOGISTICS",
  "van hire", "TRANSPORT & LOGISTICS"
)
stopifnot(!any(duplicated(livelihood_map$key)), all(livelihood_map$category %in% categories))

raw <- lapply(sheets, function(s) read_excel(input_file, sheet = s, col_types = "text"))
names(raw) <- sheets
sapply(raw, nrow)

get_col <- function(df, exact = NULL, prefix = NULL) {
  nm <- if (!is.null(exact)) names(df)[names(df) == exact] else names(df)[startsWith(names(df), prefix)]
  if (length(nm) == 0) rep(NA_character_, nrow(df)) else df[[nm[1]]]
}

pick_sheet <- function(df, district) {
  tibble(
    district = district,
    source_row = seq_len(nrow(df)),
    ds_raw = get_col(df, exact = "DS Division"),
    gender_raw = get_col(df, exact = "Participant Gender"),
    female_raw = get_col(df, prefix = "Female Headed"),
    age_raw = get_col(df, exact = "Participant Age"),
    disability_raw = get_col(df, prefix = "Participant Disability"),
    aswesuma_raw = get_col(df, prefix = "Aswesuma Category"),
    livelihood_text = get_col(df, exact = "Livelihood")
  )
}

rows <- bind_rows(lapply(sheets, function(s) pick_sheet(raw[[s]], s))) %>%
  mutate(is_synthetic = district != "Ampara" & source_row > n_real)

table(rows$district, rows$is_synthetic)

yes_no <- function(x) {
  v <- str_to_lower(str_squish(x))
  case_when(v == "yes" ~ "Yes", v == "no" ~ "No", TRUE ~ NA_character_)
}

rows <- rows %>%
  mutate(
    ds_division = str_to_title(str_squish(ds_raw)),
    ds_division = if_else(ds_division == "Badalkmbura", "Badalkumbura", ds_division),
    gender = case_when(
      str_to_upper(str_squish(gender_raw)) == "F" ~ "Female",
      str_to_upper(str_squish(gender_raw)) == "M" ~ "Male",
      TRUE ~ NA_character_),
    female_headed = yes_no(female_raw),
    disability = yes_no(disability_raw),
    age = suppressWarnings(as.numeric(age_raw)),
    age = if_else(!is.na(age) & (age < 15 | age > 100), NA_real_, age),
    aswesuma_category = case_when(
      str_to_lower(str_squish(aswesuma_raw)) == "severely poor" ~ "Severely Poor",
      str_to_lower(str_squish(aswesuma_raw)) == "poor" ~ "Poor",
      str_to_lower(str_squish(aswesuma_raw)) == "vulnerable" ~ "Vulnerable",
      TRUE ~ NA_character_),
    livelihood_key = str_squish(str_remove(str_to_lower(livelihood_text), "^\\s*:+\\s*"))
  ) %>%
  left_join(livelihood_map, by = c("livelihood_key" = "key"))

sum(!is.na(rows$livelihood_text) & is.na(rows$category))

participants_clean <- rows %>%
  select(district, source_row, ds_division, gender, female_headed, age,
         disability, aswesuma_category, livelihood_text, category, is_synthetic)

model1_training <- participants_clean %>% filter(!is.na(category))

nrow(participants_clean)
nrow(model1_training)
table(model1_training$category, model1_training$is_synthetic)
table(model1_training$district, model1_training$category)
round(colMeans(is.na(model1_training)), 2)
table(model1_training$gender, useNA = "ifany")
table(model1_training$female_headed, useNA = "ifany")
table(model1_training$disability, useNA = "ifany")
table(model1_training$aswesuma_category, useNA = "ifany")
table(model1_training$ds_division, useNA = "ifany")
summary(model1_training$age)

stopifnot(nrow(participants_clean) == 659, nrow(model1_training) == 363,
          sum(model1_training$is_synthetic) == 62)

write_csv(participants_clean, file.path(out_dir, "participants_clean.csv"))
write_csv(model1_training, file.path(out_dir, "model1_training.csv"))
list.files(out_dir)