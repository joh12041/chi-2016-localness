# Example script for running Multivariate and Univariate Spatial Regression Decisions
# Author: Isaac L. Johnson, University of Minnesota, joh12041@cs.umn.edu

if ("spdep" %in% rownames(installed.packages()) == FALSE) {
    install.packages("spdep")
}
library(spdep)

source("../assign_significance_code.R")
source("../multivariate_sar_main.R")
source("../multivariate_sar_tree.R")
source("../univariate_sar_main.R")
source("../univariate_sar_tree.R")

LogScaleZeroesToMinPosSkew <- function(dataFrame, startColNum, endColNum, printSDs = FALSE) {
  #@params
  #dataFrame: R data frame
  #startColNum: column index number of first column in dataframe to be transformed
  #endColNum: column index number of last column in dataframe to be transformed
  
  for(i in startColNum : endColNum) {
    dataFrame[i] <- log(dataFrame[i])
    if (identical(min(dataFrame[i]), -Inf)) {
      realmin <- min(dataFrame[dataFrame[i] != -Inf, i])
      dataFrame[dataFrame[i] == -Inf, i] <- realmin
    }
    if (printSDs) {
      cat(colnames(dataFrame[i]))
      cat(" - STDEV post log transformation, prior to scaling: ")
      cat(sapply(dataFrame[i], sd))
      cat("\n")
      cat(colnames(dataFrame[i]))
      cat(" - MEAN post log transformation, prior to scaling: ")
      cat(sapply(dataFrame[i], mean))
      cat("\n")
    }
    dataFrame[i] <- scale(dataFrame[i])
  }
  return (dataFrame)
}


usc_data <- read.csv("example_us_data.csv", header=TRUE)  # Colnames: FIPS, EnwikiPctLocalTokens, PctPopUrban, HMI, MedAge, VoteRate4D, PctWNL, PctMBSA
usc_7nn <- read.gwt2nb("../resources/USContiguousCounties_7nn.gwt", region.id=usc_data$FIPS)

print("Summary Input Data:")
print(summary(usc_data))
print("Summary Scaled Input Data:")
print(summary(scale(usc_data[2:8])))
print("Summary Log-transformed + Scaled Input Data:")
print(summary(LogScaleZeroesToMinPosSkew(usc_data, 2, 8)))

usc_data <- LogScaleZeroesToMinPosSkew(usc_data, 4, 4, printSDs = TRUE)
usc_data <- LogScaleZeroesToMinPosSkew(usc_data, 8, 8, printSDs = TRUE)
print("Standard Deviations and Means non-transformed variables prior to scaling:")
print(sapply(usc_data[2:3], sd))
print(sapply(usc_data[2:3], mean))
usc_data[2:3] <- scale(usc_data[2:3])
print(sapply(usc_data[5:7], sd))
print(sapply(usc_data[5:7], mean))
usc_data[5:7] <- scale(usc_data[5:7])

cat("\n\n\n\n")
print("Summary of final dataset:")
print(summary(usc_data))
cat("\n\n\n\n")

print("Running Univariate Models")
UnivariateSAR(dataFrame = usc_data, neighbor = usc_7nn, startDVColNum = 2, endDVColNum = 2, startIVColNum = 3, endIVColNum = 8)
print("Running Multivariate Model")
MultivariateSAR(dataFrame = usc_data, neighbor = usc_7nn, startDVColNum = 2, endDVColNum = 2, ivList = "PctPopUrban + HMI + MedAge + VoteRate4D + PctWNL + PctMBSA")
