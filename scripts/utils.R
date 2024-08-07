library(dplyr)
library(purrr)
library(rhdf5)
library(stringr)

process_hdf5_files <- function(hdf5_files, required_frames) {
  hdf5_files %>%
    map_dfr(~{
      # The "/timeseries_data" contains per-worm and per-frame measurements (ex curvature_mean_tail_abs_IQR).
      # Susceptible to NAs, but NAs might be useful to winnow to high-signal data.
      # This is probably the main readout we'll use for estimating phenotypes.
      timeseries_data <- h5read(.x, name = "/timeseries_data")
      
      # We need a distinct worm_index for each worm.
      # Grab folder that nd2 sits in, which right now is our unique identifier.
      # This might need to change for subsequent experiments.
      # file_id <- str_extract(basename(dirname(.x)), "^[^\\.]+")
      # just parse file_id after bc it will change per experiment
        
      processed_data <- timeseries_data %>%
        mutate(file_id = .x,
               across(everything(), ~replace(., is.nan(.), NA))) %>%
        select(-well_name) %>%  # Remove well_name column
        filter(!if_all(-c(worm_index, timestamp), is.na))  # Filter out rows that are all NA except for the first two columns
      
      # Filter based on number of frames.
      # If there aren't enough frames of the worm, it usually means that Tierpsy tracker had trouble measuring that worm.
      # When this is the case, the data have a lot of NAs.
      # Alternatively, few frames could mean that the worm entered into the field of view during mid-capture.
      # I'm not sure how to compare mid-capture worms against normal worms, so for now we don't discriminate between these two failure modes,
      # we just remove everything that doesn't have plentiful frames.
      processed_data %>%
        group_by(worm_index) %>%
        filter(n() > required_frames) %>%
        ungroup() 
    })
}

parse_file_id <- function(df, type = c("filename", "dirname")) {
 if(type == "dirname"){
   df %>%
      mutate(file_id = str_extract(basename(dirname(file_id)), "^[^\\.]+"))
 }
 else {
   df %>%
      mutate(file_id = str_extract(basename(file_id), "^[^\\.]+")) %>%
      mutate(file_id = str_remove(string = file_id, pattern = "_featuresN"))
 }
}


filter_incomplete_tierpsy_observations <- function(df, na_fraction = 0.1) {
  # df: a data frame representing *featuresN.hdf5 information produced by Tierpsy tracker
  # na_fraction: the minimum fraction of observations that can have an NA.
  #    For example, if na_fraction is set to 0.1, a row will only be kept in the
  #    data frame if fewer than 10% of it's columns are NAs. The lower this
  #    number is, the more rows that will be removed.
  df_na <- df %>%
    rowwise() %>%
    mutate(na_count = sum(is.na(across(everything()))),
           total_count = ncol(.),
           na_fraction = na_count / total_count) %>%
    filter(na_fraction < 0.1) %>%
    select(-na_count, -total_count, -na_fraction)
  
  # remove the columns that still have NA rows to produce complete cases
  na_columns_report <- df_na %>%
    summarise(across(everything(), ~sum(is.na(.)), .names = "{.col}")) %>%
    pivot_longer(cols = everything(), names_to = "column_name", values_to = "na_count") %>%
    filter(na_count > 0) %>%
    group_by(column_name) %>%
    tally()
  
  df_filtered <- df_na %>%
    select(-all_of(na_columns_report$column_name))
  
  # check that we have complete cases only
  nrow(df_filtered) == nrow(complete(df_filtered))
  
  return(df_filtered)
}

# Function to find the longest continuous stretch of timestamps from a data frame.
# Returns a dataframe that only includes the frames from the longest stretch
find_longest_frame_stretch_df <- function(df) {
  # catch rowwise grouped data, which will mess with the rest of the calculations
  df <- df %>% ungroup()
  # Sort and calculate differences
  df <- df %>%
    mutate(timestamp = as.numeric(timestamp)) %>%
    arrange(timestamp) %>%
    mutate(diff = c(1, diff(timestamp)))
  
  # Identify continuous segments
  df <- df %>%
    mutate(group = cumsum(diff > 1))
  
  # Calculate the length of each segment
  lengths <- df %>%
    group_by(group) %>%
    summarise(length = n(), .groups = 'drop')
  
  # Determine the group with the maximum length
  max_group <- lengths[which.max(lengths$length), "group"] %>%
    pull(group)
  
  # Filter the original data frame to this group only
  longest_data <- df %>%
    filter(group == max_group) %>%
    select(-group, -diff) 
  
  return(longest_data)
}
