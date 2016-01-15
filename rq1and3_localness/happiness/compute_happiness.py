"""RQ3: Happiness algorithm as impacted by localness"""

import csv
import os
import argparse
from collections import OrderedDict

import numpy
from scipy.stats import spearmanr
from scipy.stats import wilcoxon

from ..utils import bots

LOCALNESS_METRICS = ['nday','plurality']
HAPPINESS_EVALUATIONS_FN = "../resources/happiness_evaluations.txt"


def build_happiness_dict():
    """Return dictionary containing word : happiness."""
    with open(HAPPINESS_EVALUATIONS_FN, 'r') as fin:
        csvreader = csv.reader(fin, delimiter='\t')
        # Clear out metadata
        for i in range(0, 3):
            next(csvreader)
        assert next(csvreader) == ['word', 'happiness_rank', 'happiness_average', 'happiness_standard_deviation', 'twitter_rank', 'google_rank', 'nyt_rank', 'lyrics_rank']
        happy_dict = {}
        for line in csvreader:
            word = line[0]
            h_avg = float(line[2])
            if h_avg > 6 or h_avg < 4:
                happy_dict[word] = h_avg

    return happy_dict


def compute_happiness(scale='counties'):
    """Compute happiness by county based on localness-processed CSV from localness.py."""

    # generate word -> happiness dictionary
    happy_dict = build_happiness_dict()
    bots_filter = bots.build_bots_filter()

    # directory containing all of the tweets sorted by state or county depending on scale - one file for each region
    tweets_dir = './{0}'.format(scale)
    tweets_fns = os.listdir(tweets_dir)

    output_fn = "./raw_happiness_results_{0}.csv".format(scale)
    with open(output_fn, "w") as fout:
        csvwriter = csv.writer(fout)
        for localness in LOCALNESS_METRICS:
            csvwriter.writerow(['{0}_fips'.format(scale), '{0}_med_h'.format(localness), '{0}_avg_h'.format(localness),
                                'nonlocal_med_h', 'nonlocal_avg_h', 'unfiltered_med_h', 'unfiltered_avg_h',
                                'total_local', 'total_nonlocal', 'local_excluded', 'nonlocal_excluded'])
            local_filtered_out = 0
            nonlocal_filtered_out = 0
            for file in tweets_fns:
                with open(os.path.join(tweets_dir, file), 'r') as fin:
                    fips = os.path.splitext(file)[0]  # files named by <FIPS-CODE>.csv
                    csvreader = csv.reader(fin)
                    header = ['text','uid','nday','plurality']
                    txt_idx = header.index('text')
                    uid_idx = header.index('uid')
                    localness_idx = header.index(localness)
                    assert next(csvreader) == header
                    local_tweets = []
                    lt_no_happy_words = 0
                    non_local = []
                    nl_no_happy_words = 0
                    for line in csvreader:
                        txt = line[txt_idx]
                        uid = line[uid_idx]
                        if not line[localness_idx]:
                            continue
                        local = (line[localness_idx] == 'True')
                        if uid in bots_filter:
                            if local:
                                local_filtered_out += 1
                            else:
                                nonlocal_filtered_out += 1
                            continue
                        total_happ = 0.0
                        count_words = 0
                        for word in txt.split():
                            cleaned = word.lower().strip('?!.,;:()[]{}"\'')
                            if cleaned in happy_dict:
                                count_words += 1
                                total_happ += happy_dict[cleaned]
                        if count_words > 0:
                            h_avg_txt = total_happ / count_words
                            if local:
                                local_tweets.append(h_avg_txt)
                            else:
                                non_local.append(h_avg_txt)
                        else:
                            if local:
                                lt_no_happy_words += 1
                            else:
                                nl_no_happy_words += 1

                    local_med_h = numpy.median(local_tweets)
                    local_avg_h = numpy.average(local_tweets)
                    nonlocal_med_h = numpy.median(non_local)
                    nonlocal_avg_h =  numpy.average(non_local)
                    unfiltered_med_h = numpy.median(local_tweets + non_local)
                    unfiltered_avg_h = numpy.average(local_tweets + non_local)
                    csvwriter.writerow([fips, local_med_h, local_avg_h, nonlocal_med_h, nonlocal_avg_h, unfiltered_med_h,
                                        unfiltered_avg_h, len(local_tweets), len(non_local), lt_no_happy_words, nl_no_happy_words])
            print("{0} 'local' tweets and {1} 'nonlocal' tweets filtered out from organizations for {2}.".format(local_filtered_out, nonlocal_filtered_out, localness))

    process_happiness_results(scale, output_fn)


def process_happiness_results(scale, input_fn):
    """
    Go through all counties/states happiness results and filter for counties with sufficient tweets to produce rankings
    :param scale: counties or states
    :return: writes rankings to CSV
    """
    tweet_threshold = 3000  # minimum "happiness" tweets for county to be considered
    output_fn = "happiness_rankings_{0}_min{1}tweets.csv".format(scale, tweet_threshold)

    # include county/state names for easier evaluation of results
    fips_to_county = {}
    with open('../resources/fips_to_names.csv', 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['FIPS','STATE','COUNTY']
        for line in csvreader:
            fips = line[0]
            if scale == 'counties':
                if len(fips) == 4:
                    fips = '0' + fips
                fips_to_county[fips] = '{0}, {1}'.format(line[2], line[1])
            else:
                fips = fips[:2]
                fips_to_county[fips] = line[1]

    # read in raw results by county/state from analyzing all tweets - four tables in succession for each localness metric
    with open(input_fn, "r") as fin:
        csvreader = csv.reader(fin)
        idx = 0
        localness = LOCALNESS_METRICS[idx]
        header = ['{0}_fips'.format(scale), '{0}_med_h'.format(localness), '{0}_avg_h'.format(localness),
                  'nonlocal_med_h', 'nonlocal_avg_h', 'unfiltered_med_h', 'unfiltered_avg_h', 'total_local',
                  'total_nonlocal', 'local_excluded', 'nonlocal_excluded']
        assert next(csvreader) == header
        total_local_idx = header.index('total_local')
        total_nonlocal_idx = header.index('total_nonlocal')
        fips_idx = header.index('counties_fips')
        local_havg_idx = header.index('{0}_avg_h'.format(localness))
        nonlocal_havg_idx = header.index('nonlocal_avg_h')
        unfiltered_havg_idx = header.index('unfiltered_avg_h')

        # aggregate unfiltered, local, and nonlocal happiness by county/state for generating rankings
        data = {}
        for line in csvreader:
            if line[0] == header[0]:  # have reached next localness metric
                idx += 1
                localness = LOCALNESS_METRICS[idx]
            else:
                total_local = float(line[total_local_idx])
                total_nonlocal = float(line[total_nonlocal_idx])
                fips = fips_to_county[line[fips_idx]]
                local_havg = line[local_havg_idx]
                nonlocal_havg = line[nonlocal_havg_idx]
                unfiltered_havg = line[unfiltered_havg_idx]
                if total_local + total_nonlocal >= tweet_threshold:  # if sufficiently robust number of tweets for comparing to other counties/states
                    pct_local = total_local / (total_local + total_nonlocal)
                    if fips in data:
                        data[fips]['{0}_local'.format(localness)] = local_havg
                        data[fips]['{0}_nonlocal'.format(localness)] = nonlocal_havg
                        data[fips]['{0}_pct_local'.format(localness)] = pct_local
                        data[fips]['total_local_{0}'.format(localness)] = total_local
                        data[fips]['total_nonlocal_{0}'.format(localness)] = total_nonlocal
                    else:
                        data[fips] = {'county' : fips,
                                      'total_tweets' : total_local + total_nonlocal,
                                      'total_local_{0}'.format(localness) : total_local,
                                      'total_nonlocal_{0}'.format(localness) : total_nonlocal,
                                      '{0}_local'.format(localness) : local_havg,
                                      '{0}_nonlocal'.format(localness) : nonlocal_havg,
                                      'unfiltered' : unfiltered_havg,
                                      '{0}_pct_local'.format(localness) : pct_local}

    ranks = []
    unfiltered = {}
    for i in range(1, len(data) + 1):
        ranks.append({})
    # sort results by unfiltered happiest to saddest
    sd = OrderedDict(sorted(data.items(), key=lambda x: x[1]['unfiltered'], reverse=True))
    for i, fips in enumerate(sd):
        ranks[i]['county'] = fips
        ranks[i]['unfiltered'] = i + 1
        ranks[i]['total_tweets'] = sd[fips]['total_tweets']
        unfiltered[fips] = i
    for localness in LOCALNESS_METRICS:
        for property in ['local','nonlocal']:
            sd = {}
            for k in data:
                if '{0}_{1}'.format(localness, property) in data[k]:
                    sd[k] = data[k]
            # sort happiest to saddest for localness metric + local or nonlocal
            sd = OrderedDict(sorted(sd.items(), key=lambda x: x[1]['{0}_{1}'.format(localness, property)], reverse=True))
            # write ranking for that metric and (non)local to the row where the unfiltered county name is (so sorting any given column by rankings has the correct county labels to understand it)
            for i, fips in enumerate(sd):
                ranks[unfiltered[fips]]['{0}_{1}'.format(localness, property)] = i + 1

    # write out rankings
    with open(output_fn, 'w') as fout:
        header = ['county', 'total_tweets', 'unfiltered']
        for property in ['local','nonlocal']:
            for localness in LOCALNESS_METRICS:
                header.append('{0}_{1}'.format(localness, property))
        csvwriter = csv.DictWriter(fout, fieldnames=header, extrasaction='ignore')
        csvwriter.writeheader()
        for rank in ranks:
            csvwriter.writerow(rank)

    # generate Spearman's rho comparing unfiltered to each localness metric and counting geographies that changed dramatically
    ten_pct_threshold = int(len(ranks) * 0.1)
    for localness in LOCALNESS_METRICS:
        for property in ['local','nonlocal']:
            metric = []
            uf = []
            ten_pct_diff = 0
            name = '{0}_{1}'.format(localness, property)
            for rank in ranks:
                if name in rank:
                    uf.append(rank['unfiltered'])
                    metric.append(rank[name])
                    if abs(rank[name] - rank['unfiltered']) >= ten_pct_threshold:
                        ten_pct_diff += 1
            rho, pval = spearmanr(metric,uf)
            print('{0}:'.format(name))
            print("Spearman's rho between {0} and unfiltered rankings is {1} with a p-value of {2}.".format(name, rho, pval))
            print("{0} counties out of {1} were more than {2} rankings different than the unfiltered results.".format(ten_pct_diff, len(ranks), ten_pct_threshold))
            stat, pval = wilcoxon(metric, uf, zero_method="pratt")
            print("Wilcoxon statistic between {0} and unfiltered rankings is {1} with a p-value of {2}.\n".format(name, stat, pval))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", default = "counties", help = "compute happiness by either 'states' or 'counties'")
    args = parser.parse_args()
    compute_happiness(scale = args.scale)

if __name__ == "__main__":
    main()