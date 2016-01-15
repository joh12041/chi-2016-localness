DrawVariableDistribution <- function(dataFrame, startColNum, endColNum) {
    # Draw distribution histogram of all variables between @startColNum and @endColNum
    # Written by Yilun (Allen) Lin, University of Minnesota
    #
    # Args:    
    #   dataFrame: R data frame that contains the variables whose distribution is to be plotted
    #   startColNum: the column index of first variable to draw
    #   endColNum: the column index of last variable to draw

    for (i in startColNum : endColNum) {
        iv <- colnames(dataFrame)[i]
        h <- hist(as.numeric(dataFrame[i][, 1]), breaks = "FD", freq = FALSE, main = paste("Distribution of ", iv))
        curve(dnorm(x, mean = mean(dataFrame[i][, 1]), sd = sd(dataFrame[i][, 1])), add = TRUE, col = "darkblue", lwd = 2)
        outputName <- paste(deparse(substitute(dataFrame)), paste(iv), ".pdf", sep="")
        dev.copy2pdf(file = outputName, onefile = FALSE)
        dev.off()
    }
}
