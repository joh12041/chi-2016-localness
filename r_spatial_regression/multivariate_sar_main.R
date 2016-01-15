MultivariateSAR <- function(dataFrame, neighbor, startDVColNum, endDVColNum, ivList){
    # Runs MultivariateSpatialRegressionDecision tree on dataframe for a dependent variable and a given set of independent variables
    # Written by Yilun (Allen) Lin, University of Minnesota
    #
    # Args:
    #   dataFrame: R data frame containing dependent and independent variables
    #   neighbor: spatial weights matrix file from Geoda. from spdep read.gal or read.gwt2nb, left as type nb
    #   startDVColNum: the start column number of the Dependent Variable
    #   endDVColNum: the ending column number of Dependent Variables
    #   ivList: quoted list of independent variable names to appear on right side of a regression (e.g., "INC + HOVAL")
    #
    # Returns:
    #   Writes out Multivariate SAR results to given file


    outTable <- c()
    res <- NULL
    resColNames <- c()

    for (m in startDVColNum : endDVColNum) {  # loop through dependent variables
        dvName <- colnames(dataFrame)[m]
        formulaReg <- formula(paste(dvName, "~", ivList))
        formulaReg
        resColNames <- cbind(resColNames, dvName)
        outputName <- paste(dvName, "_x_MultipleVariables.txt", sep = "")
        # Run Spatial Regression Decision Function
        cat("\nRunning Spatial Regression Decision with: ")
        print(formulaReg)
        cat("\n")
        output <- MultivariateSpatialRegressionDecision(formulaReg, dataFrame, neighbor, outputName, outTable, res)
        outTable <- output$outTable
        res <- output$res
        cat("\n\n\n\n\n\n")
    }
    tablenames <-  c("call",
                     "Model_type",
                     "Intercept",
                     "OLS_AdjustR^2",
                     "SAR_PseudoR^2",
                     "loglik/lm_loglik",
                     "AIC/LM_AIC",
                     "lambda_rho",
                     "Wald_Test",
                     "LR_Test",
                     "BPTest",
                     "LMError")
    for (IV in strsplit(ivList, split = "+", fixed = TRUE)) {
        tablenames <- c(tablenames, IV)
    }
    colnames(outTable) <- tablenames
    write.csv(file = paste("MultivariateSAR.csv"), outTable)
    colnames(res) <- resColNames
    multivariate_residuals <<- res
}
