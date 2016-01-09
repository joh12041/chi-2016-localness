UnivariateSpatialRegressionDecision <- function(formula, dataFrame, neighbor, outputName, outTable) {
    # Evaluates univariate spatial data and makes decision to run an OLS model or the proper spatial regression model
    # Written by Yilun (Allen) Lin, University of Minnesota
    #
    # Args:
    #   formula: R Formula such as CRIME ~ INC
    #   dataFrame: R data frame/table containing columns specified in formula
    #   neighbor: spatial weights matrix file from Geoda. from spdep read.gal or read.gwt2nb, left as type nb
    #   outputName: in quotations; file will be created in working directory or will overwrite existing file
    #   outTable: R data frame/table to which output summary statistics are appended
    #
    # Returns:
    #   outTable to which are appended the results from the regression that is run

    #Reload the spdep in case it is not loaded
    library(spdep)

    # Running the OLS
    cat("Running Classic OLS Regression...\n")
    ols <- lm(formula, data=dataFrame)

    # Write the formula
    capture.output(print(formula), file=outputName, append=TRUE)
    cat("\n\n\n", file=outputName, append=TRUE)

    # Write OLS Regression Result to the file
    cat("==============================\nOLS Regression Result:\n", file=outputName, append=TRUE)
    capture.output(summary(ols), file=outputName, append=TRUE)
    cat("==============================\n\n\n", file=outputName, append=TRUE)

    # Build the spatial weight list
    listW <- nb2listw(neighbor)

    # Moran's I test for spatial autocorrelation in OLS residual
    cat("Running Moran's I test on Classic OLS Regression's residual ...\n")
    residualMoranTest <- lm.morantest(ols, listW)
    residualMoranP <- residualMoranTest$p.value

    cat("==============================\nMoran's I test against the OLS regression residual:\n", file=outputName, append=TRUE)

    # Checks for significance in spatial autocorrelation
    if (residualMoranP < 0.05) {
        cat("P-value for OLS Regression Residual Moran's I test is: ", residualMoranP, ", and it's significant. Run Lagrangian Multipler Test to decide which SAR model to use\n")
        capture.output(print(residualMoranTest), file=outputName, append=TRUE)
        cat("==============================\n\n\n", file=outputName, append=TRUE)

        # Run Lagrangian Multipler Test
        cat("Running Lagrangian Multiplier Test...\n")
        lagrangianTest <- lm.LMtests(ols, listW, test="all")

        # Write Lagrangian Test Result to the file
        cat("==============================\nLagrangian Multiplier Test on the OLS Regression Result:\n", file=outputName, append=TRUE)
        capture.output(print(lagrangianTest), file=outputName, append=TRUE)
        cat("==============================\n\n\n", file=outputName, append=TRUE)

        # Output the p-value of Lagrangian Multiplier Test
        cat("p-value of LMerr is: ", lagrangianTest$LMerr$p.value, "p-value of LMlag is: ", lagrangianTest$LMlag$p.value, "\n")

        # LM values for both spatial lag and error models are significant
        if (lagrangianTest$LMerr$p.value < 0.05 & lagrangianTest$LMlag$p.value < 0.05) {
            cat("Both LMerr and LMlag are significant. Compare Robust LMerr and Robust LMlag\n")
            cat("p-value of Robust LMerr is: ", lagrangianTest$LMerr$p.value, "... p-value of Robust LMlag is: ", lagrangianTest$LMlag$p.value, "\n")

            # If both LMerr and LMlag are significant, check if RLMerr or RLMlag are significant
            if (lagrangianTest$RLMerr$p.value < 0.05 | lagrangianTest$RLMlag$p.value < 0.05) {
                if (lagrangianTest$RLMlag$p.value < lagrangianTest$RLMerr$p.value) {
                    cat("Robust LMlag is more significant! Use SAR Lag Model\n")
                    sarResult <- lagsarlm(formula, data=dataFrame, listW)
                } else {
                    cat("Robust LMerror is more significant! Use SAR Error Model\n")
                    sarResult <- errorsarlm(formula, data=dataFrame, listW)
                }
            } else { # Neither RLMerror nor RLMlag are significant. The more significant model is still run for data.
                cat("Neither Robust are significant. Model misspecification. Smaller p-value will be run but results should be evaluated.")
                cat("==============================\nNeither Robust are significant. Model misspecification. Smaller p-value will be run but results should be evaluated:\n", file=outputName, append=TRUE)
                cat("==============================\n\n\n", file=outputName, append=TRUE)

                if (lagrangianTest$RLMerr$p.value < lagrangianTest$RLMlag$p.value) {
                    sarResult <- errorsarlm(formula, data=dataFrame, listW)
                } else {
                    sarResult <- lagsarlm(formula, data=dataFrame, listW)
                }
            }
        }
        # LM values for only one of the lag or error models is significant
        else if (lagrangianTest$LMerr$p.value < 0.05 | lagrangianTest$LMlag$p.value < 0.05) {
            # Choose the SAR model with smaller LM p-value
            cat("Only one of LMerr and LMlag is significant. The SAR model with smaller p-value will be used.\n")
            if (lagrangianTest$LMlag$p.value < 0.05) {
                cat("LMlag is more significant! Use SAR Lag Model\n")
                sarResult <- lagsarlm(formula, data=dataFrame, listW)
            } else if (lagrangianTest$LMerr$p.value < 0.05) {
                cat("LMerror is more significant! Use SAR Error Model\n")
                sarResult <- errorsarlm(formula, data=dataFrame, listW)
            }
        } else { # Neither LM values for lag nor error were significant. OLS result retained.
            cat("Even though Residual Moran's I was significant (", residualMoranP, "), neither LMerr (", lagrangianTest$LMerr$p.value, ") or LMlag (", lagrangianTest$LMlag$p.value, ") are significant. Stick with OLS.\n")
            cat("==============================\n","Even though Residual Moran's I was significant (", residualMoranP, "), neither LMerr (", lagrangianTest$LMerr$p.value, ") or LMlag (", lagrangianTest$LMlag$p.value, ") are significant. Stick with OLS.\n", file=outputName, append=TRUE)
            cat("==============================\n\n\n", file=outputName, append=TRUE)
            sarResult <- ols
        }
    } else { # Moran's I does not indicate spatial autocorrelation in OLS residuals
        cat("P-value for OLS Residual Moran's I test is: ", residualMoranP, ", and it's NOT significant. Stop and use OLS\n")
        cat("==============================\n","P-value for OLS Residual Moran's I test is: ", residualMoranP, ", and it's NOT significant. Stop and use OLS\n", file=outputName, append=TRUE)
        sarResult <- ols
    }
    #Write the Final Regression Result to the file
    cat("==============================\n The Final Regression Result:\n", file=outputName, append=TRUE)
    capture.output(summary(sarResult), file=outputName, append=TRUE)
    cat("==============================\n\n\n", file=outputName, append=TRUE)

    sarResult
    cat(sarResult$type)
    # Decide if SAR or OLS is run and construct the output Table
    if (!is.null(sarResult$type)) {
        # Parse the DV Name from the formula
        dvName <- paste0(as.list(attr(terms(formula), "variables"))[2])

        # Compute the Pseudo-R^2
        sarResult.fitted <- fitted.values(sarResult)
        sarResult.lm <- lm(dataFrame[, dvName] ~ sarResult.fitted)
        pseudoRSquared <- summary(sarResult.lm)$r.squared

        # If SAR is used, report the result
        if (sarResult$type == "error") {
            spatialAutoregressiveCoefficient <- sarResult$lambda
        } else if (sarResult$type == "lag") {
            spatialAutoregressiveCoefficient <- sarResult$rho
        }
        estimatePValue <- 2 * (1 - pnorm(abs(sarResult$coefficients / sarResult$rest.se)))
        # Note that "-"/negative sign at the beginning of a cell will cause Excel to treat the cell as a formula. To avoid this, a space is added at the beginning of a cell
        outTable <- rbind(outTable,
                          c(formula,
                            sarResult$type,
                            paste0(round(sarResult$coefficients[2], 4), AssignSignCode(estimatePValue[2])),
                            round(summary(ols)$adj.r.squared, 4),
                            round(pseudoRSquared, 4),
                            paste0(" ", round(sarResult$LL, 4), "/", round(sarResult$logLik_lm.model, 4)),
                            paste0(round(AIC(sarResult), 4), "/", round(sarResult$AIC_lm.model, 4)),
                            round(spatialAutoregressiveCoefficient, 4),
                            paste0(round(Wald1.sarlm(sarResult)$statistic, 4), AssignSignCode(Wald1.sarlm(sarResult)$p.value)),
                            paste0(round(LR1.sarlm(sarResult)$statistic, 4), AssignSignCode(LR1.sarlm(sarResult)$p.value))))
    } else { #If OLS is used, report partial results
        outTable <- rbind(outTable,
                          c(formula,
                            "OLSResult",
                            paste0(ols$coefficients[2], AssignSignCode(summary(ols)$coefficients[2, 4])),
                            summary(ols)$adj.r.squared,
                            "pseudoRSquared",
                            "LogLik_PH",
                            "AIC_PH",
                            "SAC_PH",
                            "WaldT_PH",
                            "LRTest_PH"))
    }
    return (outTable)
}
