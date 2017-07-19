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

## Additional Tables ##

Percentage of VGI from each repository that all (N, P, G, L) or just NPG agree upon as local or non-local. Non-local includes VGI for which the user had not been assigned a local county.

| Repository | % All Local | % All Nonlocal | % All Agreed | % NPG Local | % NPG Nonlocal | % NPG Agreed |
| ---------- | ----------: | -------------: | -----------: | ----------: | -------------: | -----------: |
| T-51M | 15.1% | 5.0% | 20.1% | 76.9% | 5.1% | 82.0% |
| T-15M | 21.4% | 8.9% | 30.3% | 52.8% | 9.2% | 62.0% |
| F-15M | 13.9% | 16.2% | 30.1% | 30.2% | 16.3% | 46.5% |
| S-8M | 0.2% | 10.3% | 10.5% | 62.3% | 10.3% | 72.6% |

## Corrections ##
The original version of the paper, under the section *Different Localness Definitions, Different Results*, contained a sentence that read:

>"Each localness metric operationalizes a different idea of localness, and, as such, it is not a surprise that they frequently disagree as to whether a user can be considered a local to a county. Plurality, n-days and geometric median agreed the most, but for users for which all three could determine at least one local county, their output overlapped by at least one county only 76.9% of the time for T-51M, and that is the highest agreement of any of the four repositories."

This sentence has since been corrected because that statistic 76.9% refers to VGI (not users) and includes all VGI, not just that of users who have at least one local county. The original sentiment holds true that there is a non-trivial percentage of social media for which localness is ambiguous:

>"Each localness metric operationalizes a different idea of localness, and, as such, it is not a surprise that they frequently disagree as to whether an individual piece of VGI can be considered a local to a county. Plurality, n-days and geometric median agreed the most, but, for instance, their output agreed that a given tweet was local only 76.9% of the time for T-51M, and that is the highest agreement of any of the four repositories."
