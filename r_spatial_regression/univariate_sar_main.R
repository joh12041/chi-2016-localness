UnivariateSAR <- function(dataFrame, neighbor, startDVColNum, endDVColNum, startIVColNum, endIVColNum) {
    # Runs UnivariateSpatialRegressionDecision tree on dataframe for a dependent variable and a given set of independent variables
    # Written by Yilun (Allen) Lin, University of Minnesota
    #
    # Args:
    #   dataFrame: R data frame containing dependent and independent variables
    #   neighbor: spatial weights matrix file from Geoda. from spdep read.gal or read.gwt2nb, left as type nb
    #   startDVColNum: the start column number of the Dependent Variable
    #   endDVColNum: the ending column number of Dependent Variables
    #   startIVColNum: starting column number for the Independent Variables to be tested for univariate regression
    #   endIVColNum: ending column number for the Independent Variables to be tested for univariate regression
    #
    # Returns:
    #   Writes out Univariate SAR results to given file

    outTable <- c()

    for (m in startDVColNum : endDVColNum) {  # loop through dependent variables
        dvName <- colnames(dataFrame)[m]
        for (i in startIVColNum : endIVColNum) {  # for each DV, test all independent variables one at a time
            iv <- colnames(dataFrame)[i]
            formulaReg <- formula(paste(dvName, "~", iv))
            formulaReg
            outputName <- paste(dvName, "_x_", iv, ".txt", sep="")

            # Run Spatial Regression Decision Function
            cat("\nRunning Spatial Regression Decision with: ")
            print(formulaReg)
            cat("\n")
            outTable <- UnivariateSpatialRegressionDecision(formulaReg, dataFrame, neighbor, outputName, outTable)
            cat("\n\n\n\n\n\n")
        }
    }
    colnames(outTable) <- c("call",
                            "Model_type",
                            "Estimate of Coefficient (Pvalue)",
                            "OLS_AdjustR^2",
                            "SAR_PseudoR^2",
                            "loglik/lm_loglik",
                            "AIC/LM_AIC",
                            "lambda_rho",
                            "Wald_Test",
                            "LR_Test")
    write.csv(file = paste("UnivariateSAR.csv"), outTable)
}
