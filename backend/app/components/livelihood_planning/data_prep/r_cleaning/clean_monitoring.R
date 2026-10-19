# Clean the monthly household monitoring form (v5)

library(readxl)
library(dplyr)
library(tidyr)
library(stringr)
library(readr)
library(tibble)
library(lubridate)

input_file <- "C:/Users/MSI/Desktop/SLIIT/RESEARCH PROJECT/Final_Datasets/WB_Monthly_Household_Monitoring_Form_v5.xlsx"
out_dir    <- "cleaned_monitoring"
MIN_GROUP  <- 5

stopifnot(file.exists(input_file))
dir.create(out_dir, showWarnings = FALSE)

CATS <- c("AGRICULTURE & PLANTATION CROPS", "LIVESTOCK & ANIMAL HUSBANDRY", "FOOD PROCESSING & PRODUCTION",
          "TRADE", "GARMENT TEXTILE, HANDICRAFTS", "CONSTRUCTION, BUILDING AND REPAIR",
          "TRANSPORT & LOGISTICS", "BEAUTY AND WELLNESS", "OTHER")

raw <- read_excel(input_file, sheet = 1, guess_max = 10000)
cat("Rows read:", nrow(raw), " Columns:", ncol(raw), "\n")

cleaning_log <- tibble(rule = character(), rows_or_cells = integer(), note = character())
log_step <- function(rule, n, note = "") {
  cleaning_log <<- bind_rows(cleaning_log, tibble(rule = rule, rows_or_cells = as.integer(n), note = note))
}

pick <- function(pattern) {
  hit <- grep(pattern, names(raw), value = TRUE)
  if (length(hit) != 1) stop("Column pattern '", pattern, "' matched ", length(hit), " columns")
  raw[[hit]]
}

txt     <- function(x) str_squish(as.character(x))
is_dk   <- function(x) str_detect(txt(x), regex("^Don.t know", ignore_case = TRUE))
is_na_ans <- function(x) str_detect(txt(x), regex("^Not applicable", ignore_case = TRUE))

yn <- function(x, name = NULL) {
  t <- str_to_lower(txt(x))
  out <- case_when(t == "yes" ~ TRUE, t == "no" ~ FALSE, TRUE ~ NA)
  if (!is.null(name)) log_step(paste0("Don't know / Not applicable -> NA: ", name), sum(is_dk(x) | is_na_ans(x), na.rm = TRUE))
  out
}

to_date <- function(x) {
  if (inherits(x, "POSIXt")) return(as.Date(x))
  if (inherits(x, "Date"))   return(x)
  if (is.numeric(x))         return(as.Date(x, origin = "1899-12-30"))
  as.Date(parse_date_time(as.character(x), orders = c("Ymd HMS", "Ymd", "Y/m/d", "dmY"), quiet = TRUE))
}

# Identity and flags
hh_key <- txt(pick("^household_key$"))
hh_key[hh_key == ""] <- NA

d <- tibble(
  visit_id          = sprintf("V%04d", seq_len(nrow(raw))),
  source_uuid       = txt(pick("^_uuid$")),
  household_id      = hh_key,
  monitoring_period = txt(pick("^monitoring_period$")),
  visit_date        = to_date(pick("^Date of SDO household visit$"))
) %>%
  mutate(month_index = match(monitoring_period, sort(unique(monitoring_period))))

stopifnot(!anyDuplicated(d$source_uuid))
log_step("Rows kept (no row deleted)", nrow(d))

# Location and household
district_raw <- txt(pick("^1\\.10\\. Participant District"))
ds_raw       <- txt(pick("^1\\.11\\. Participant Divisional"))
d$district   <- str_to_title(district_raw)
d$ds_division <- str_to_title(ds_raw)
d$ds_division[d$ds_division == "Hahiyanganaya"] <- "Mahiyanganaya"
log_step("District spelling standardised (title case)", sum(district_raw != d$district, na.rm = TRUE))
log_step("DS division spelling standardised (case, HAHIYANGANAYA typo)", sum(ds_raw != d$ds_division, na.rm = TRUE))

g_ben <- txt(pick("^1\\.2\\. Gender"))
g_par <- txt(pick("^1\\.6\\. Gender"))
log_step("Gender typo fixed (Mele -> Male)", sum(g_ben == "Mele", na.rm = TRUE) + sum(g_par == "Mele", na.rm = TRUE))
fix_gender <- function(x) { x <- str_to_title(x); x[x == "Mele"] <- "Male"; x[!x %in% c("Male", "Female")] <- NA; x }
d$beneficiary_gender <- fix_gender(g_ben)
d$participant_gender <- fix_gender(g_par)
d$female_headed      <- yn(pick("^1\\.3\\. "))
age <- suppressWarnings(as.numeric(pick("^1\\.7\\. ")))
log_step("Age outside 18-90 set to NA", sum(!is.na(age) & (age < 18 | age > 90)))
age[!is.na(age) & (age < 18 | age > 90)] <- NA
d$age <- age
q1 <- txt(pick("^Q1\\. "))
d$first_visit <- case_when(str_detect(q1, "^Yes") ~ TRUE, str_detect(q1, "^No") ~ FALSE, TRUE ~ NA)
d$cyclone_affected <- yn(pick("^2\\.1\\. Have you been"))

# Livelihood
cat_raw <- str_to_upper(txt(pick("^3\\.1\\. ")))
cat_map <- c(
  "GARMENT TEXTILE, LEATHER & HANDICRAFTS" = "GARMENT TEXTILE, HANDICRAFTS",
  "GARMENT TEXTILE & LEATHER"              = "GARMENT TEXTILE, HANDICRAFTS",
  "MISCELLANEOUS / OTHER"                  = "OTHER",
  "MISCELLANEOUS"                          = "OTHER",
  "RETAIL & WHOLESALE TRADING"             = "TRADE",
  "FISHERIES & AQUACULTURE"                = "OTHER"
)
cat_clean <- if_else(cat_raw %in% names(cat_map), unname(cat_map[cat_raw]), cat_raw)
bad <- setdiff(unique(cat_clean[!is.na(cat_clean)]), CATS)
if (length(bad)) stop("Unmapped livelihood labels: ", paste(bad, collapse = " | "))
log_step("Livelihood label mapped to the 9 official categories", sum(cat_raw != cat_clean, na.rm = TRUE))

d$category       <- if_else(is.na(cat_clean), "UNASSIGNED", cat_clean)
d$category_known <- d$category != "UNASSIGNED"
log_step("Rows with no livelihood type -> UNASSIGNED (kept, not guessed)", sum(!d$category_known))

act <- txt(pick("^3\\.2\\. Primary"))
act_clean <- case_when(
  is.na(act) | act == "" ~ NA_character_,
  str_detect(act, regex("^Tailoring", ignore_case = TRUE)) ~ "Tailoring / stitching",
  str_detect(act, regex("^Livestock farming", ignore_case = TRUE)) ~ "Livestock farming (poultry, goats)",
  str_detect(act, regex("^Snack food", ignore_case = TRUE)) ~ "Snack food production",
  TRUE ~ act
)
d$activity <- if_else(is.na(act_clean) & d$category_known, "Not specified", act_clean)
log_step("Primary activity names merged / shortened", sum(act != act_clean, na.rm = TRUE))

# Business outcome
d$business_running <- yn(pick("^3\\.3\\. "))
d$hours_band       <- txt(pick("^3\\.4\\. "))

rec <- txt(pick("^3\\.5\\. "))
d$record_keeping <- if_else(is_dk(rec), NA_character_, rec)
d$record_keeping_level <- case_when(
  str_detect(d$record_keeping, regex("don.t keep", ignore_case = TRUE)) ~ 0L,
  str_detect(d$record_keeping, regex("few times a month", ignore_case = TRUE)) ~ 1L,
  str_detect(d$record_keeping, regex("once or twice", ignore_case = TRUE)) ~ 2L,
  str_detect(d$record_keeping, regex("^daily", ignore_case = TRUE)) ~ 3L,
  TRUE ~ NA_integer_)
log_step("Don't know -> NA: record keeping", sum(is_dk(rec), na.rm = TRUE))

d$borrowed_money <- yn(pick("^3\\.6\\. "), "borrowed money")

rev <- txt(pick("^3\\.7\\. "))
d$revenue_band <- case_when(
  str_detect(rev, "^LKR 0")        ~ "LKR 0-10,000",
  str_detect(rev, "10,001")        ~ "LKR 10,001-20,000",
  str_detect(rev, "20,001")        ~ "LKR 20,001-30,000",
  str_detect(rev, "More than")     ~ "More than LKR 30,000",
  TRUE ~ NA_character_)
d$revenue_mid_lkr <- case_when(d$revenue_band == "LKR 0-10,000" ~ 5000, d$revenue_band == "LKR 10,001-20,000" ~ 15000,
                               d$revenue_band == "LKR 20,001-30,000" ~ 25000, d$revenue_band == "More than LKR 30,000" ~ 35000,
                               TRUE ~ NA_real_)
log_step("Don't know -> NA: revenue band", sum(is_dk(rev), na.rm = TRUE))

d$profit            <- yn(pick("^3\\.8\\. "), "profit")
d$coach_progressing <- yn(pick("^3\\.9\\. "), "coach: progressing well")

# Problems
d$problem_sales_low           <- yn(pick("^3\\.10\\.1\\."), "problem: sales low")
d$problem_asset_lost          <- yn(pick("^3\\.10\\.2\\."), "problem: asset lost")
d$problem_input_cost          <- yn(pick("^3\\.10\\.3\\."), "problem: input cost")
d$problem_input_unavailable   <- yn(pick("^3\\.10\\.4\\."), "problem: input unavailable")
d$problem_storage_transport   <- yn(pick("^3\\.10\\.5\\."), "problem: storage/transport")
d$problem_equipment           <- yn(pick("^3\\.10\\.6\\."), "problem: equipment")
d$problem_disaster            <- yn(pick("^3\\.10\\.7\\."), "problem: natural disaster")
prob_cols <- c("problem_sales_low", "problem_asset_lost", "problem_input_cost", "problem_input_unavailable",
               "problem_storage_transport", "problem_equipment", "problem_disaster")
d$problem_count <- if_else(rowSums(!is.na(d[prob_cols])) == 0, NA_integer_, as.integer(rowSums(d[prob_cols], na.rm = TRUE)))

# Household wellbeing and programme actions
d$skipped_meal           <- yn(pick("^4\\.1\\. "), "skipped a meal")
d$children_in_school     <- yn(pick("^4\\.2\\. "), "children attended school")
d$ill_member_got_care    <- yn(pick("^4\\.3\\. "), "ill member accessed care")
d$saved_money            <- yn(pick("^4\\.4\\. "), "saved money")
saved <- suppressWarnings(as.numeric(pick("^4\\.5\\. ")))
n_fill0 <- sum(is.na(saved) & d$saved_money %in% FALSE)
saved[is.na(saved) & d$saved_money %in% FALSE] <- 0
log_step("Saved amount set to 0 when household did not save (logical fill)", n_fill0)
d$saved_amount_lkr       <- saved
d$did_agreed_actions     <- yn(pick("^5\\.1\\. "), "did agreed actions")
d$referral_reached       <- yn(pick("^5\\.3\\. In the past month"), "reached referral")
d$goals_need_adjustment  <- yn(pick("^5\\.6\\. "))

# Grant
gr <- txt(pick("^6\\.1\\. "))
d$grant_received <- case_when(str_detect(gr, "^Yes") ~ TRUE, gr == "No" ~ FALSE, TRUE ~ NA)
d$grant_use_status <- case_when(
  gr == "No" ~ "Not received",
  str_detect(gr, regex("Not fully utilized", ignore_case = TRUE)) ~ "Received, not fully used",
  str_detect(gr, regex("bills are not settled", ignore_case = TRUE)) ~ "Received, fully used, bills not settled",
  str_detect(gr, regex("Fully utilized", ignore_case = TRUE)) ~ "Received, fully used",
  TRUE ~ NA_character_)
d$grant_used_per_plan <- yn(pick("^6\\.3\\.1\\. "))
d$grant_spent_lkr     <- suppressWarnings(as.numeric(pick("^6\\.5\\.1\\. ")))
d$grant_remaining_lkr <- suppressWarnings(as.numeric(pick("^6\\.5\\.2\\. ")))
d$refund_required     <- yn(pick("^6\\.6\\.1\\. "))
neg <- sum(d$grant_spent_lkr < 0 | d$grant_remaining_lkr < 0, na.rm = TRUE)
log_step("Negative grant amounts found (should be 0)", neg)

# Data dictionary decides the final column order
dict <- tribble(
  ~column, ~description,
  "visit_id", "Sequential visit id created during cleaning (V0001...)",
  "source_uuid", "Original submission id from the form",
  "household_id", "Household key as given in the file (blank where the visit has no household key)",
  "monitoring_period", "Month of the visit (YYYY-MM)",
  "month_index", "1 = first month in the data",
  "visit_date", "Date of the SDO household visit",
  "first_visit", "TRUE if first visit under the programme (NA if not asked)",
  "district", "Participant district (standardised)",
  "ds_division", "Participant DS division (standardised)",
  "beneficiary_gender", "Gender of the Aswesuma beneficiary",
  "participant_gender", "Gender of the programme participant",
  "female_headed", "Household headed by a female",
  "age", "Participant age (NA if missing or outside 18-90)",
  "cyclone_affected", "Household affected by the cyclone (NA if not asked)",
  "category", "One of the 9 official livelihood categories, or UNASSIGNED",
  "category_known", "FALSE when the livelihood type was not recorded",
  "activity", "Primary livelihood activity (standardised)",
  "business_running", "Is the business running",
  "hours_band", "Average hours per day worked in the livelihood (band)",
  "record_keeping", "How often written business records were kept",
  "record_keeping_level", "0 = none, 1 = few times a month, 2 = once or twice a week, 3 = daily",
  "borrowed_money", "Borrowed money for the business in the last month",
  "revenue_band", "Revenue band for the last month (NA = don't know or not running)",
  "revenue_mid_lkr", "Mid-point of the revenue band (assumption, for rough comparison only)",
  "profit", "Made a profit in the last month (NA = don't know or not running)",
  "coach_progressing", "Coach view: participant progressing well",
  "problem_sales_low", "Problem: sales less than expected",
  "problem_asset_lost", "Problem: lost a livelihood asset",
  "problem_input_cost", "Problem: high cost of inputs",
  "problem_input_unavailable", "Problem: inputs not available",
  "problem_storage_transport", "Problem: storage or transport",
  "problem_equipment", "Problem: equipment not working",
  "problem_disaster", "Problem: natural disaster",
  "problem_count", "Number of problems answered Yes (NA if none answered)",
  "skipped_meal", "A household member skipped a meal in the last 2 weeks",
  "children_in_school", "All children 6-16 attended school at least 4 days a week",
  "ill_member_got_care", "A significantly ill member accessed medical care",
  "saved_money", "Household saved money in the last month",
  "saved_amount_lkr", "Amount saved (0 when the household did not save)",
  "did_agreed_actions", "Did the agreed family-plan actions",
  "referral_reached", "Reached out to a referral person or organisation",
  "goals_need_adjustment", "Participant thinks goals need adjustment",
  "grant_received", "Grant received",
  "grant_use_status", "How the grant was used",
  "grant_used_per_plan", "Coach view: grant used as planned",
  "grant_spent_lkr", "Approximate amount spent so far",
  "grant_remaining_lkr", "Remaining balance",
  "refund_required", "Refund required"
)
stopifnot(all(dict$column %in% names(d)))
visits <- d %>% select(all_of(dict$column))

# Summaries
flag_cols <- c("business_running", "profit", "coach_progressing", prob_cols,
               "borrowed_money", "saved_money", "skipped_meal", "did_agreed_actions", "grant_received")

make_summary <- function(df, groups, level) {
  df %>%
    group_by(across(all_of(groups))) %>%
    summarise(
      n_visits            = n(),
      n_households_keyed  = n_distinct(household_id, na.rm = TRUE),
      across(all_of(flag_cols), list(n = ~sum(!is.na(.x)), yes = ~sum(.x, na.rm = TRUE)), .names = "{.col}_{.fn}"),
      rev_n               = sum(!is.na(revenue_band)),
      rev_0_10k           = sum(revenue_band == "LKR 0-10,000", na.rm = TRUE),
      rev_10_20k          = sum(revenue_band == "LKR 10,001-20,000", na.rm = TRUE),
      rev_20_30k          = sum(revenue_band == "LKR 20,001-30,000", na.rm = TRUE),
      rev_over_30k        = sum(revenue_band == "More than LKR 30,000", na.rm = TRUE),
      records_n           = sum(!is.na(record_keeping_level)),
      records_none        = sum(record_keeping_level == 0, na.rm = TRUE),
      records_daily       = sum(record_keeping_level == 3, na.rm = TRUE),
      mean_problem_count  = round(mean(problem_count, na.rm = TRUE), 3),
      .groups = "drop") %>%
    mutate(level = level, meets_min_group = n_visits >= MIN_GROUP) %>%
    relocate(level)
}

known <- visits %>% filter(category_known)
summary_all <- bind_rows(
  make_summary(known, "category",                "category"),
  make_summary(known, c("category", "district"), "category_district"),
  make_summary(known, c("category", "activity"), "activity")
) %>% relocate(any_of(c("category", "district", "activity")), .after = level)

cat_month <- make_summary(known, c("category", "monitoring_period"), "category_month") %>%
  relocate(any_of(c("category", "monitoring_period")), .after = level)

# Checks
stopifnot(nrow(visits) == nrow(raw),
          !anyDuplicated(visits$visit_id),
          all(visits$category %in% c(CATS, "UNASSIGNED")),
          !any(visits$beneficiary_gender == "Mele", na.rm = TRUE),
          all(visits$revenue_band %in% c(NA, "LKR 0-10,000", "LKR 10,001-20,000", "LKR 20,001-30,000", "More than LKR 30,000")),
          all(summary_all$profit_yes <= summary_all$profit_n))

not_running_with_profit <- sum(visits$business_running %in% FALSE & !is.na(visits$profit))
log_step("Visits where business not running but profit answered (should be 0)", not_running_with_profit)

completeness <- tibble(column = names(visits), pct_missing = round(100 * colMeans(is.na(visits)), 1)) %>% arrange(desc(pct_missing))

cat("\n--- Visits by livelihood ---\n")
print(count(visits, category))
cat("\n--- Livelihoods and the minimum group size ---\n")
print(summary_all %>% filter(level == "category") %>% select(category, n_visits, meets_min_group))
cat("\n--- Columns with most missing values (%) ---\n")
print(head(completeness, 12))
cat("\n--- Cleaning log ---\n")
print(cleaning_log, n = Inf)

# Write files
write_csv(visits,       file.path(out_dir, "monitoring_visits_clean.csv"),    na = "")
write_csv(summary_all,  file.path(out_dir, "monitoring_summary.csv"),         na = "")
write_csv(cat_month,    file.path(out_dir, "monitoring_category_month.csv"),  na = "")
write_csv(dict,         file.path(out_dir, "monitoring_data_dictionary.csv"), na = "")
write_csv(bind_rows(cleaning_log, tibble(rule = "Missing-value report: see completeness below", rows_or_cells = NA_integer_, note = "")),
          file.path(out_dir, "monitoring_cleaning_log.csv"), na = "")
write_csv(completeness, file.path(out_dir, "monitoring_completeness.csv"),    na = "")
cat("\nDone. Files saved in:", normalizePath(out_dir), "\n")

