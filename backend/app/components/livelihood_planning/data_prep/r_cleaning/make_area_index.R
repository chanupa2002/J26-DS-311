
library(readxl)
library(dplyr)
library(readr)

input_file <- "C:/Users/MSI/Desktop/SLIIT/RESEARCH PROJECT/Cleaned Datasets Final/BRIGHT_clean_all_sheets.xlsx"
out_file   <- "area_index.csv"

districts <- c("Colombo", "Gampaha", "Kalutara", "Galle", "Hambantota", "Matara",
               "Jaffna", "Kilinochchi", "Mannar", "Mullaitivu", "Vavuniya", "Ampara",
               "Batticaloa", "Trincomalee", "Anuradhapura", "Polonnaruwa", "Kandy",
               "Matale", "Nuwara Eliya", "Kurunegala", "Puttalam", "Badulla",
               "Monaragala", "Kegalle", "Ratnapura")

stopifnot(file.exists(input_file))

hh <- read_excel(input_file, sheet = "mod_a_household_identification") %>%
  transmute(hhcode, district = districts[as.integer(a_02_district)])

debt <- read_excel(input_file, sheet = "mod_n1_debt") %>%
  transmute(hhcode, has_debt = n1_0 == 1)

land_hh <- read_excel(input_file, sheet = "mod_e_land_long") %>%
  distinct(hhcode) %>%
  mutate(has_land = TRUE)

items <- sprintf("l1_%02d", 1:8)
food <- read_excel(input_file, sheet = "mod_l1_food_security_w") %>%
  select(hhcode, all_of(items)) %>%
  filter(if_all(all_of(items), ~ .x %in% c(1, 2))) %>%
  mutate(food_score = rowSums(across(all_of(items)) == 1)) %>%
  select(hhcode, food_score)

food_by_district <- hh %>%
  inner_join(food, by = "hhcode") %>%
  group_by(district) %>%
  summarise(food_insecurity_score = round(mean(food_score), 2), .groups = "drop")

area_index <- hh %>%
  left_join(debt, by = "hhcode") %>%
  left_join(land_hh, by = "hhcode") %>%
  mutate(has_land = coalesce(has_land, FALSE)) %>%
  group_by(district) %>%
  summarise(debt_pct = round(100 * mean(has_debt, na.rm = TRUE), 1),
            land_pct = round(100 * mean(has_land), 1),
            .groups = "drop") %>%
  left_join(food_by_district, by = "district") %>%
  select(district, food_insecurity_score, debt_pct, land_pct) %>%
  slice(match(districts, district))

stopifnot(nrow(area_index) == 25, !anyNA(area_index))

write_csv(area_index, out_file)
cat("Wrote", out_file, "with", nrow(area_index), "districts\n")

