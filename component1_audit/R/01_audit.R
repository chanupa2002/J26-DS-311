# Component 1 reproducible module audit. Base R only; inputs are read-only.
here <- normalizePath(getwd(), winslash="/", mustWork=FALSE)
project_dir <- if (basename(here) == "component1_audit") here else file.path(here,"component1_audit")
clean_dir <- Sys.getenv("BRIGHT_CLEAN_DIR", unset="C:/data/processed/clean")
processed_dir <- Sys.getenv("BRIGHT_PROCESSED_DIR", unset="C:/data/processed")
out_dir <- file.path(project_dir,"outputs")
if (!dir.exists(clean_dir)) clean_dir <- normalizePath(file.path(project_dir,"..","Data","processed","clean"), winslash="/", mustWork=TRUE)
if (!dir.exists(processed_dir)) processed_dir <- normalizePath(file.path(project_dir,"..","Data","processed"), winslash="/", mustWork=TRUE)
dir.create(out_dir,recursive=TRUE,showWarnings=FALSE)

type_label <- function(x) {
  x <- x[!is.na(x) & nzchar(x)]
  if (!length(x)) return("all_missing")
  if (all(x %in% c("0","1","TRUE","FALSE"))) return("binary_like")
  if (all(!is.na(suppressWarnings(as.numeric(x))))) return("numeric")
  if (all(!is.na(as.Date(x,tryFormats=c("%Y-%m-%d","%d/%m/%Y"))))) return("date")
  "text_or_code"
}

build_inventory <- function(clean_dir, processed_dir) {
  keyfile <- file.path(processed_dir,"cleaning_log.csv")
  log <- if (file.exists(keyfile)) read.csv(keyfile,stringsAsFactors=FALSE,check.names=FALSE,na.strings="") else data.frame()
  files <- sort(list.files(clean_dir,pattern="\\.csv$",full.names=TRUE,ignore.case=TRUE))
  stopifnot(length(files)>0)
  rows <- lapply(files,function(f) {
    x <- read.csv(f,stringsAsFactors=FALSE,check.names=FALSE,colClasses="character",na.strings=c("","NA"),
                  strip.white=FALSE,blank.lines.skip=TRUE)
    stem <- tools::file_path_sans_ext(basename(f))
    li <- if(nrow(log)) match(stem,log$sheet) else NA_integer_
    keys <- if(!is.na(li) && nzchar(log$key_cols[li])) strsplit(log$key_cols[li],"\\+")[[1]] else if("hhcode" %in% names(x)) "hhcode" else character()
    keys <- intersect(keys,names(x))
    dup <- if(length(keys)) sum(duplicated(x[keys])) else NA_integer_
    miss <- vapply(x,function(z) sum(is.na(z)),integer(1))
    types <- vapply(x,type_label,character(1))
    grain <- if(length(keys)>1 && any(grepl("pid|person|member",keys))) "person/member record" else if(grepl("employment",stem)) "employment record" else if(grepl("j1|j2|nfe|_long",stem)) "repeated item/event; inspect key fields" else if(length(keys)==1 && keys=="hhcode") "household-shaped export" else "entity grain needs review"
    data.frame(filename=basename(f),rows=nrow(x),columns=ncol(x),variable_names=paste(names(x),collapse=" | "),
      variable_types=paste(paste(names(types),types,sep=":"),collapse=" | "),key_fields=paste(keys,collapse="+"),
      key_missing_rows=if(length(keys)) sum(!complete.cases(x[keys])) else NA_integer_,duplicate_key_rows=dup,
      observation_grain=grain,missingness_by_variable=paste(sprintf("%s:%d (%.2f%%)",names(miss),miss,100*miss/max(1,nrow(x)))[miss>0],collapse=" | "),
      stringsAsFactors=FALSE,check.names=FALSE)
  })
  do.call(rbind,rows)
}

inventory <- build_inventory(clean_dir,processed_dir)
write.csv(inventory,file.path(out_dir,"module_inventory_R.csv"),row.names=FALSE,na="")
# A long, machine-comparable missingness table makes future drift testable.
miss_rows <- list()
for (f in sort(list.files(clean_dir,pattern="\\.csv$",full.names=TRUE,ignore.case=TRUE))) {
  x <- read.csv(f,stringsAsFactors=FALSE,check.names=FALSE,colClasses="character",na.strings=c("","NA"),
                strip.white=FALSE,blank.lines.skip=TRUE)
  m <- vapply(x,function(z) sum(is.na(z)),integer(1))
  miss_rows[[length(miss_rows)+1L]] <- data.frame(filename=basename(f),variable=names(m),missing_n=as.integer(m),
      pct_missing=100*m/max(1,nrow(x)),stringsAsFactors=FALSE,check.names=FALSE)
}
write.csv(do.call(rbind,miss_rows),file.path(out_dir,"module_missingness_R.csv"),row.names=FALSE,na="")
message("R audit inventory written: ",nrow(inventory)," modules")
