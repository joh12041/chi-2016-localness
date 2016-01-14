# Full Localness Results #

## RQ1 ##

Raw counts and percent local results for each repository under RQ1 in the paper. For each repository, there are 3109 counties. The categories that do not end in `_TOTAL` are mutually exclusive. That is, `ALL` means that each of the localness metrics found that piece of VGI to be local and therefore it will not be counted under any of the other categories such as `NDAY`. The categories are set up so that a piece of VGI is counted in the most restrictive category in which it falls (i.e. all metrics is checked first followed by combinations of three, then two, then one, and finally none if the VGI is not local by any of the metrics). In the Twitter datasets, there is also a category for `BOTS` which supersedes all of the other categories and contains VGI that came from users marked as organizations/bots.

The `_TOTAL` categories reflect the total proportion of VGI for that county that was local per that metric. It is a sum across multiple categories (e.g., for `N_TOTAL`, VGI is counted from `ALL`, `NDAY`, `NPG`, `NPL`, `NGL`, `NP`, `NG`, and `NL`).

### Glossary ###
- N = *ndays (10)*
- P = *plurality*
- G = *geometric median*
- L = *location field*

## RQ2 ##
Formatted results for the R spatial regressions run on the percentage of VGI that was local to a county. This file can be used as input to `python-utils/compute_effect_size_statements.py` to generate effect-size statements based off of the regression results.

## RQ3 ##
Full rankings for the happiness results by counties and states. Details explained in the paper.
