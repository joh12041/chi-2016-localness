AssignSignCode <- function(pValue) {
    # Returns a significance code based on an input p-value.
    # Written by Yilun (Allen) Lin, University of Minnesota
    #
    # Args:
    #   pValue: numeric p-value for evaluation
    #
    # Returns:
    #   The symbolic code for the appropriate level of significance.
    if (pValue < 0.001) {
        return("***")
    } else if (pValue < 0.01) {
        return("**")
    } else if (pValue < 0.05) {
        return("*")
    } else if (pValue < 0.1) {
        return(".")
    } else {
        return("")
    }
}
