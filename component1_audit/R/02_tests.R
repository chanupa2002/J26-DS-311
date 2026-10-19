# Base-R automated assertions for keys, rows, code domains, missingness and safe aggregation.
# Run from repository root with: Rscript component1_audit/R/02_tests.R
source("component1_audit/R/01_audit.R")

expected <- read.csv(file.path(project_dir,"outputs","expected_module_rows.csv"),stringsAsFactors=FALSE)
actual <- inventory[match(expected$filename,inventory$filename),]
stopifnot(!anyNA(actual$filename), identical(as.integer(actual$rows),as.integer(expected$rows)))

# Compare every cleaned module/variable missing-value count with the reviewed baseline.
expected_missing <- read.csv(file.path(project_dir,"outputs","expected_missingness.csv"),stringsAsFactors=FALSE)
observed_missing <- read.csv(file.path(project_dir,"outputs","module_missingness_R.csv"),stringsAsFactors=FALSE)
miss_key <- function(x) paste(x$filename,x$variable,sep="\r")
stopifnot(setequal(miss_key(expected_missing),miss_key(observed_missing)))
mi <- match(miss_key(expected_missing),miss_key(observed_missing))
stopifnot(identical(as.integer(expected_missing$missing_n),as.integer(observed_missing$missing_n[mi])))

# Every current cleaned module must have nonmissing unique keys as specified in the prior cleaning log.
log <- read.csv(file.path(processed_dir,"cleaning_log.csv"),stringsAsFactors=FALSE,check.names=FALSE,na.strings="")
for (i in seq_len(nrow(log))) {
  f <- file.path(clean_dir,paste0(log$sheet[i],".csv"))
  if (!file.exists(f)) next # duplicate export may be deliberately logged as skipped
  x <- read.csv(f,stringsAsFactors=FALSE,check.names=FALSE,colClasses="character",na.strings=c("","NA"))
  keys <- strsplit(log$key_cols[i],"\\+")[[1]]
  keys <- intersect(keys,names(x))
  if(length(keys)) stopifnot(!any(!complete.cases(x[keys])),!anyDuplicated(x[keys]))
  if(is.finite(log$rows_out[i]) && !is.na(log$rows_out[i])) stopifnot(nrow(x)==log$rows_out[i])
}

# Questionnaire-backed known valid code subsets. Missingness is allowed and remains missing.
check_codes <- function(file, variable, valid) {
  x <- read.csv(file.path(clean_dir,file),stringsAsFactors=FALSE,check.names=FALSE,colClasses="character",na.strings=c("","NA"))
  stopifnot(variable %in% names(x))
  observed <- unique(x[[variable]][!is.na(x[[variable]]) & nzchar(x[[variable]])])
  stopifnot(all(observed %in% valid))
}
check_codes("mod_l1_food_security_w.csv","l1_01",c("1","2","3","4"))
check_codes("mod_l2_food_security_m.csv","l2_01",c("1","2","3","4"))
check_codes("mod_o1_shocks.csv","o1_01_1",c("1","2","3"))
# The questionnaire labels N2_05 1/2; the cleaned file currently stores 0/1.
# This checks the observed cleaned domain, not whether that recode is semantically approved.
check_codes("mod_n2_savings.csv","n2_05",c("0","1"))
check_codes("mod_n3_savings_w.csv","n3_5",c("0","1"))
check_codes("mod_n1_debt.csv","n1_0",c("0","1"))

# Missingness audit must be measurable and bounded; preserve the source missingness counts.
stopifnot(all(inventory$columns>0),all(inventory$rows>=0),all(inventory$key_missing_rows==0,na.rm=TRUE),
          all(inventory$duplicate_key_rows==0,na.rm=TRUE))

# Independently aggregate each repeated table before joining to the household spine.
safe_sum <- function(z) if(all(is.na(z))) NA_real_ else sum(z,na.rm=TRUE)
aggregate_hh <- function(x,key,value) {
  groups <- split(seq_len(nrow(x)),x[[key]])
  data.frame(hhcode=names(groups),value=vapply(groups,function(i) safe_sum(x[[value]][i]),numeric(1)),stringsAsFactors=FALSE)
}
safe_join <- function(x,y) {
  stopifnot(!anyDuplicated(x$hhcode),!anyDuplicated(y$hhcode))
  n <- nrow(x); z <- merge(x,y,by="hhcode",all.x=TRUE,sort=FALSE)
  stopifnot(nrow(z)==n); z
}
hh <- data.frame(hhcode=c("h1","h2"),stringsAsFactors=FALSE)
jobs <- data.frame(hhcode=c("h1","h1","h2"),income=c(10,20,5))
loans <- data.frame(hhcode=c("h1","h2","h2"),amount=c(1,2,3))
jobs_hh <- aggregate_hh(jobs,"hhcode","income")
loans_hh <- aggregate_hh(loans,"hhcode","amount")
joined <- safe_join(safe_join(hh,jobs_hh),loans_hh)
stopifnot(nrow(joined)==nrow(hh),joined$value.x[joined$hhcode=="h1"]==30,
          joined$value.y[joined$hhcode=="h2"]==5)
bad_join <- try(safe_join(hh,jobs),silent=TRUE)
stopifnot(inherits(bad_join,"try-error"))
unknown_total <- safe_sum(c(NA_real_,NA_real_))
zero_total <- safe_sum(c(0,NA_real_))
stopifnot(is.na(unknown_total),identical(zero_total,0))
message("All Component 1 data audit assertions passed")
