"""Compute effect size statements based on the results of R spatial regressions.

Requires knowledge of the transformation applied to both the dependent and independent variables as well as the standard deviations of all variables prior to scaling. Log refers to a natural log transformation. If log-10 is used, different constants need to be used in the calculations."""

import csv
import argparse
import math

METADATA = [["pct_urban", {"stdev": 0.314, "transformation": "scaled", "header":"PCT_URBAN_POP_MULTIVARIATE_BETA", "abbr":"UP"}],  # 31.4% Urban Pop
            ["hmi", {"stdev": 0.2405, "transformation": "logged-scaled", "header":"HMI_MULTIVARIATE_BETA", "abbr":"HMI"}],  # originally $11791, 0.2405 post-log-transformation
            ["med_age", {"stdev": 5, "transformation": "scaled", "header":"MED_AGE_MULTIVARIATE_BETA", "abbr":"MA"}],  # 5 years
            ["wnl", {"stdev": 0.195, "transformation": "scaled", "header":"WNL_MULTIVARIATE_BETA", "abbr":"WNL"}],  # 19.5% White, Non-Latino
            ["mbsa", {"stdev": 0.198, "transformation": "logged-scaled", "header":"MBSA_MULTIVARIATE_BETA", "abbr":"MBSA"}]]  # originally 19.8% Management/Business/Science/Art

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--regression_file",default="results/rq2.csv", help="file path of the the csv file containing the R spatial regression results.")
    parser.add_argument("--output_file", default="regression_effect_size_statements.csv", help="file path of the csv file that will contain the regression results with effect size statements appended.")
    args = parser.parse_args()

    with open(args.regression_file, 'r') as fin:
        with open(args.output_file, 'w') as fout:
            csvreader = csv.reader(fin)
            csvwriter = csv.writer(fout)
            header = next(csvreader)  # REPOSITORY	FILTER, DEPENDENT_VARIABLE, MODEL_TYPE, DV_TRANSFORMATION, SD_BEFORE_SCALING, PCT_URBAN_POP_MULTIVARIATE_BETA, HMI_MULTIVARIATE_BETA, MED_AGE_MULTIVARIATE_BETA, WNL_MULTIVARIATE_BETA, MBSA_MULTIVARIATE_BETA
            sd_idx = header.index("SD_BEFORE_SCALING")
            transformation_idx = header.index("DV_TRANSFORMATION")
            for iv in METADATA:
                iv[1]["header"] = header.index(iv[1]["header"])
                if iv[1]['transformation'] == "logged-scaled":
                    header.append('{0}_PlusTenPercent'.format(iv[1]["abbr"]))
                elif iv[1]['transformation'] == 'scaled':
                    header.append('{0}_PlusOneSD'.format(iv[1]["abbr"]))
                else:
                    header.append(iv[1]["abbr"])
            csvwriter.writerow(header)
            for line in csvreader:
                dv_sd = float(line[sd_idx])
                for iv in METADATA:
                    beta = line[iv[1]["header"]]
                    if "*" in beta:
                        dv_transformation = line[transformation_idx]
                        iv_transformation = iv[1]['transformation']
                        value = float(beta.replace("*",""))
                        if dv_transformation == "Logged, Scaled":
                            if iv_transformation == 'logged-scaled':
                                effect_size = "{0}% Relative Change".format(round((math.pow(1.1, value * dv_sd / iv[1]["stdev"]) - 1) * 100, 1))
                            elif iv_transformation == 'scaled':
                                effect_size = "{0}% Relative Change".format(round((math.pow(2.71828, value * dv_sd) - 1) * 100, 1))
                            else:
                                effect_size = "IV Transformation Not Supported"
                        elif dv_transformation == "Scaled":
                            if iv_transformation == "logged-scaled":
                                effect_size = "{0}% Absolute Change".format(round(math.log(1.1) * value * dv_sd / iv[1]["stdev"] * 100, 1))
                            elif iv_transformation == "scaled":
                                effect_size = "{0}% Absolute Change".format(round(value * dv_sd * 100, 1))
                            else:
                                effect_size = "IV Transformation Not Supported"
                        else:
                            effect_size = "DV Transformation Not Supported"
                    else:
                        effect_size = "Not Significant"
                    line.append(effect_size)
                csvwriter.writerow(line)


if __name__ == "__main__":
    main()
