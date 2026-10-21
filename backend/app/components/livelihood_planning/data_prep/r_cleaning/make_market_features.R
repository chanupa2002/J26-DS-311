library(readxl)
library(dplyr)
library(tidyr)
library(stringr)
library(readr)
library(tibble)

input_file  <- "C:/Users/MSI/Desktop/SLIIT/RESEARCH PROJECT/Cleaned Datasets Final/SUSTAIN_Combined_Clean.xlsx"
out_dir     <- "market_features"
MIN_MONTHS  <- 12
RECENT_FROM <- "2026-07"

stopifnot(file.exists(input_file))
dir.create(out_dir, showWarnings = FALSE)

raw <- read_excel(input_file, sheet = "Clean_Data", guess_max = 10000)
cat("Rows read:", nrow(raw), "\n")

filter_log <- tibble(step = character(), rows = integer())
log_step <- function(step, n) filter_log <<- bind_rows(filter_log, tibble(step = step, rows = as.integer(n)))
log_step("Rows read", nrow(raw))

# 1. Monthly series table (flagged rows excluded)
drop <- list(
  "Derived month-on-month rows"      = raw$Is_Derived_Feature == "Yes",
  "Prior-year comparison rows"       = raw$Is_Prior_Year_Comparator == "Yes",
  "Reporting-count rows"             = raw$Is_Metadata_Count == "Yes",
  "Incomplete last month"            = raw$Partial_Month == "Yes",
  "Outlier review flag"              = raw$Outlier_Review_Flag == "Yes",
  "OCR or secondary source to verify" = raw$Date_Quality_Flag %in% c("OCR_VERIFY", "SECONDARY_VERIFY")
)
for (nm in names(drop)) log_step(paste("Excluded:", nm), sum(drop[[nm]], na.rm = TRUE))
keep <- !Reduce(`|`, lapply(drop, function(x) x %in% TRUE))

monthly <- raw[keep, ] %>%
  transmute(series_key = Series_Key, month = Month, value = Value,
            source = Source, location = Location, category = Programme_Livelihood_Category,
            commodity = Commodity_or_Sector, indicator = Indicator, unit = Unit,
            price_type = Price_Type, coverage_tier = Coverage_Tier,
            evidence_type = if_else(Proxy_Only == "YES", "index proxy", "item price"),
            t = as.integer(str_sub(Month, 1, 4)) * 12L + as.integer(str_sub(Month, 6, 7)))
monthly <- monthly %>%
  group_by(series_key) %>%
  mutate(across(c(category, evidence_type, coverage_tier), ~ .x[which.max(t)])) %>%
  ungroup()
log_step("Rows kept in monthly series table", nrow(monthly))
stopifnot(!anyDuplicated(monthly[c("series_key", "month")]))

# 2. Trend and volatility per series
trend_one <- function(t, v) {
  o <- order(t); t <- t[o]; v <- v[o]
  y <- log(v); n <- length(t); tb <- mean(t); yb <- mean(y)
  sxx <- sum((t - tb)^2)
  b <- sum((t - tb) * (y - yb)) / sxx
  res <- y - (yb + b * (t - tb))
  se <- sqrt(sum(res^2) / (n - 2) / sxx)
  lag_change <- function(k) {
    i <- match(t - k, t); ok <- !is.na(i)
    if (!any(ok)) return(numeric(0))
    (y[ok] - y[i[ok]])
  }
  c3 <- lag_change(3)
  last_t <- max(t)
  last3 <- if ((last_t - 3) %in% t) y[t == last_t] - y[t == last_t - 3] else NA_real_
  yoy   <- if ((last_t - 12) %in% t) y[t == last_t] - y[t == last_t - 12] else NA_real_
  z3    <- if (!is.na(last3) && length(c3) >= 6 && isTRUE(sd(c3) > 0)) (last3 - mean(c3)) / sd(c3) else NA_real_
  tibble(n_months = n, slope = b, slope_se = se, p_value = 2 * pt(-abs(b / se), n - 2),
         cv = sd(v) / mean(v), change_3m_pct = 100 * (exp(last3) - 1),
         change_12m_pct = 100 * (exp(yoy) - 1), z_3m = z3)
}

series_stats <- monthly %>%
  filter(value > 0) %>%
  group_by(series_key, category, evidence_type, coverage_tier, source, commodity, indicator, unit) %>%
  filter(n_distinct(month) >= MIN_MONTHS) %>%
  summarise(first_month = min(month), last_month = max(month), trend_one(t, value), .groups = "drop")
log_step(paste0("Series with at least ", MIN_MONTHS, " months"), nrow(series_stats))

# 3. Shrink each slope toward the average of its evidence type
shrink <- function(b, se) {
  tau2 <- max(var(b) - mean(se^2), 1e-8)
  w <- tau2 / (tau2 + se^2)
  mean(b) + w * (b - mean(b))
}
series_stats <- series_stats %>%
  group_by(evidence_type) %>%
  mutate(slope_shrunk = shrink(slope, slope_se)) %>%
  ungroup() %>%
  mutate(trend_pct_per_month = round(100 * (exp(slope_shrunk) - 1), 3),
         significant = p_value < 0.05) %>%
  select(-slope, -slope_se, -slope_shrunk) %>%
  mutate(across(c(p_value, cv, change_3m_pct, change_12m_pct, z_3m), ~ round(.x, 4)))

# 4. Pressure index per livelihood and evidence type
livelihood_summary <- series_stats %>%
  group_by(category, evidence_type) %>%
  summarise(
    n_series          = n(),
    n_recent          = sum(last_month >= RECENT_FROM & !is.na(z_3m)),
    median_trend_pct_per_month = round(median(trend_pct_per_month), 3),
    share_rising_significant   = round(mean(significant & trend_pct_per_month > 0), 3),
    median_cv         = round(median(cv, na.rm = TRUE), 3),
    median_change_12m_pct = round(median(change_12m_pct, na.rm = TRUE), 2),
    pressure_z        = round(mean(z_3m[last_month >= RECENT_FROM], na.rm = TRUE), 3),
    .groups = "drop") %>%
  mutate(pressure_z = if_else(is.nan(pressure_z), NA_real_, pressure_z),
         pressure_label = case_when(is.na(pressure_z) ~ "not enough recent data",
                                    pressure_z >= 0.5 ~ "rising",
                                    pressure_z <= -0.5 ~ "falling",
                                    TRUE ~ "stable"),
         enough_series = n_series >= 3)

# 5. Disaster table by district
disaster <- raw %>%
  filter(Source == "DMC Situation Reports", str_detect(Location, " District$"),
         Indicator %in% c("Affected_Families_Latest_Report", "Affected_People_Latest_Report", "Deaths_Latest_Report")) %>%
  mutate(district = str_replace(str_remove(Location, " District$"), "^Moneragala$", "Monaragala"),
         indicator = recode(Indicator, Affected_Families_Latest_Report = "affected_families",
                            Affected_People_Latest_Report = "affected_people",
                            Deaths_Latest_Report = "deaths")) %>%
  group_by(district, month = Month, indicator) %>% summarise(value = max(Value), .groups = "drop") %>%
  pivot_wider(names_from = indicator, values_from = value) %>%
  arrange(district, month)
for (col in c("affected_families", "affected_people", "deaths")) if (!col %in% names(disaster)) disaster[[col]] <- NA_real_
disaster <- disaster %>% select(district, month, affected_families, affected_people, deaths)

# checks
stopifnot(nrow(series_stats) > 0, !anyDuplicated(series_stats$series_key),
          all(series_stats$n_months >= MIN_MONTHS))

cat("\n--- Filter log ---\n");           print(filter_log, n = Inf)
cat("\n--- Livelihood summary ---\n");   print(livelihood_summary %>% select(category, evidence_type, n_series, n_recent, median_trend_pct_per_month, pressure_z, pressure_label), n = Inf)
cat("\n--- Districts in disaster table ---\n"); print(count(disaster, district), n = Inf)

write_csv(monthly,            file.path(out_dir, "market_monthly_clean.csv"),      na = "")
write_csv(series_stats,       file.path(out_dir, "market_series_stats.csv"),       na = "")
write_csv(livelihood_summary, file.path(out_dir, "market_livelihood_summary.csv"), na = "")
write_csv(disaster,           file.path(out_dir, "market_disaster_district.csv"),  na = "")
write_csv(filter_log,         file.path(out_dir, "market_filter_log.csv"),         na = "")
cat("\nDone. Files saved in:", normalizePath(out_dir), "\n")

