__author__ = 'isaac'

import csv
import numpy
import os
import psycopg2
import psycopg2.extras
import json
from collections import OrderedDict

import sys

sys.path.append("/export/scratch2/isaacj/vgi-localness")

from utils import bots

#from scipy.stats import spearmanr
#from scipy.stats import wilcoxon

#localness_metrics = ['n','p','v','l']
localness_metrics = ['nday','plurality']


def process_happiness_results(scale, input_fn):
    """
    Go through all counties/states happiness results and filter for counties with sufficient tweets to produce rankings
    :param scale: counties or states
    :return: writes rankings to CSV
    """
    tweet_threshold = 3000  # minimum "happiness" tweets for county to be considered
    output_fn = "./happiness/happiness_by_{0}_bots_rankings_min{1}_dist_p.csv".format(scale, tweet_threshold)

    # include county/state names for easier evaluation of results
    fips_to_county = {}
    with open('happiness/fips_to_names.csv', 'r') as fin:
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
        localness = localness_metrics[idx]
        header = ['{0}_fips'.format(scale), '{0}_med_h'.format(localness), '{0}_avg_h'.format(localness), 'nonlocal_med_h', 'nonlocal_avg_h', 'unfiltered_med_h', 'unfiltered_avg_h', 'total_local', 'total_nonlocal', 'local_excluded', 'nonlocal_excluded']
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
                localness = localness_metrics[idx]
            else:
                total_local = float(line[total_local_idx])
                total_nonlocal = float(line[total_nonlocal_idx])
                fips = fips_to_county[line[fips_idx]]
                local_havg = line[local_havg_idx]
                nonlocal_havg = line[nonlocal_havg_idx]
                unfiltered_havg = line[unfiltered_havg_idx]
                if total_local >= tweet_threshold and total_nonlocal >= tweet_threshold:
                #if total_local + total_nonlocal >= tweet_threshold:  # if sufficiently robust number of tweets for comparing to other counties/states
                    pct_local = total_local / (total_local + total_nonlocal)
                    if fips in data:
                        data[fips]['{0}_local'.format(localness)] = local_havg
                        data[fips]['{0}_nonlocal'.format(localness)] = nonlocal_havg
                        data[fips]['{0}_pct_local'.format(localness)] = pct_local
                        data[fips]['total_local_{0}'.format(localness)] = total_local
                        data[fips]['total_nonlocal_{0}'.format(localness)] = total_nonlocal
                    else:
                        data[fips] = {'county':fips, 'total_tweets':total_local + total_nonlocal,
                                      'total_local_{0}'.format(localness):total_local,
                                      'total_nonlocal_{0}'.format(localness):total_nonlocal,
                                      '{0}_local'.format(localness):local_havg, '{0}_nonlocal'.format(localness):nonlocal_havg,
                                      'unfiltered':unfiltered_havg, '{0}_pct_local'.format(localness):pct_local}

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
    for localness in localness_metrics:
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
        header = ['county','total_tweets','unfiltered']
        for property in ['local','nonlocal']:
            for localness in localness_metrics:
                header.append('{0}_{1}'.format(localness, property))
        csvwriter = csv.DictWriter(fout, fieldnames=header, extrasaction='ignore')
        csvwriter.writeheader()
        for rank in ranks:
            csvwriter.writerow(rank)

    # generate Spearman's rho comparing unfiltered to each localness metric and counting geographies that changed dramatically
    ten_pct_threshold = int(len(ranks) * 0.1)
    for localness in localness_metrics:
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
            #rho, pval = spearmanr(metric,uf)
            print('{0}:'.format(name))
            #print("Spearman's rho between {0} and unfiltered rankings is {1} with a p-value of {2}.".format(name, rho, pval))
            print("{0} counties out of {1} were more than {2} rankings different than the unfiltered results.".format(ten_pct_diff, len(ranks), ten_pct_threshold))
            #stat, pval = wilcoxon(metric, uf, zero_method="pratt")
            #print("Wilcoxon statistic between {0} and unfiltered rankings is {1} with a p-value of {2}.\n".format(name, stat, pval))


def by_state():
    happiness_evaluations_fn = 'happiness/happiness_evaluations.txt'
    with open(happiness_evaluations_fn, 'r') as fin:
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

    VGI_REPOSITORY = 'twitter14'
    scale = 'states'
    tweets_fn = 'output_data/{0}/tweet_as_json_localness.csv'.format(VGI_REPOSITORY)

    conn = psycopg2.connect("dbname=twitterstream_zh_us")
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

    NDAY_MIN = 10  # days

    vgi_median_file = "vgi_median/{0}/user_counties.csv".format(VGI_REPOSITORY)
    location_field_file = "location_field/{0}/user_counties_cleaned.csv".format(VGI_REPOSITORY)

    print("Querying database for nday/plurality results...")
    cur.execute("SELECT * FROM ndaytemp_t14state;")

    print("Processing nday and plurality...")
    user_counties = {}
    for row in cur:
        uid = str(row[0])
        state = row[1]  # string
        count_VGI = row[2]  # int
        ntime = row[3]  # PostgreSQL interval converted to datetime.timedelta by psycopg2
        if uid in user_counties:
            user_counties[uid][state] = ntime.days >= NDAY_MIN
            if count_VGI > user_counties[uid]['plurality_count']:
                user_counties[uid]['plurality'] = [state]
                user_counties[uid]['plurality_count'] = count_VGI
            elif count_VGI == user_counties[uid]['plurality_count']:
                user_counties[uid]['plurality'].append(state)
        else:
            user_counties[uid] = {state : ntime.days >= NDAY_MIN, 'plurality' : [state], 'plurality_count': count_VGI}
    print("{0} users processed.".format(len(user_counties)))

    print("Processing VGI median results...")
    with open(vgi_median_file, 'r') as fin:
        csvreader = csv.reader(fin)
        # assert next(csvreader) == ['uid', 'county']
        count_vgimed = 0
        for line in csvreader:
            uid = str(line[0])
            state = line[1][:2]
            try:
                if state:
                    count_vgimed += 1
                    user_counties[uid]['median'] = state
                elif uid in user_counties:
                    user_counties[uid]['median'] = False
            # Should be no need for an try clause because if user wasn't in nday/plurality, then they didn't
            #  contribute any stateside tweets, but there's a guy who tweeted from JFK who slipped through somehow.
            except Exception as e:
                print(e, line)
                continue
    print("{0} VGI medians added.".format(count_vgimed))

    # Ignore user data because some users posted multiple locations so not all uids have a unique entry
    print("Processing location field results...")
    locations = {}
    with open(location_field_file, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['uid', 'loc_field', 'county']
        for line in csvreader:
            loc_field = line[1]
            county = line[2].split(';')  # in case multiple counties (e.g., NYC)
            for i in range(0, len(county)):
                county[i] = county[i][:2]
            locations[loc_field] = county
    print("{0} locations registered.".format(len(locations)))

    with open(tweets_fn, 'r') as fin:
        csvreader = csv.reader(fin)
        header = ['id','created_at','text','user_screen_name','user_description','user_lang',
              'user_location','user_time_zone','lon','lat','geom_src','county','gender',
              'race','uid','tweet','nday','plurality','vgimed','locfield']
        assert next(csvreader) == header
        states = {}
        state_not_found = 0
        line_no = 0
        errors = 0
        for line in csvreader:
            try:
                line_no += 1
                txt = line[header.index('text')]
                state = line[header.index('county')][:2]
                total_happ = 0.0
                count_words = 0
                uid = line[header.index('uid')]
                if state and state in user_counties[uid]:
                    if user_counties[uid][state]:  # n-day
                        n = True
                    else:
                        n = False
                    if state in user_counties[uid]['plurality']:  # plurality
                        p = False
                    else:
                        p = False
                    if state == user_counties[uid]['median']:  # vgi median
                        v = True
                    else:
                        v = False
                    try:
                        loc_field_entry = json.loads(line[header.index('tweet')])['user']['location']
                        if loc_field_entry and state in locations[loc_field_entry]:  # self-reported location
                            l = True
                        else:
                            l = False
                    except Exception:
                        print("Lookup Failed:", json.loads(line[header.index('tweet')])['user']['location'])
                        l = False
                    for word in txt.split():
                        cleaned = word.lower().strip('?!.,;:()[]{}"\'')
                        if cleaned in happy_dict:
                            count_words += 1
                            total_happ += happy_dict[cleaned]
                    if count_words > 0:
                        h_avg_txt = total_happ / count_words
                        update_localness_dict(states, n, p, v, l, state, h_avg_txt)
                    else:
                        update_localness_dict(states, n, p, v, l, state, None)
                elif state:
                    state_not_found += 1
            except Exception as e:
                print(e)
                errors += 1
                continue
            if line_no % 250000 == 0:
                print("{0} lines processed, {1} states not found, and {2} other errors.".format(line_no, state_not_found, errors))
        print("{0} states not located out {1} tweets and {2} errors.".format(state_not_found, line_no, errors))


    with open("./happiness/happiness_by_{0}_plurality.csv".format(scale), "w") as fout:
        csvwriter = csv.writer(fout)
        output_header = ['state','unfiltered_med_h', 'unfiltered_avg_h']
        for localness in localness_metrics:
            output_header.extend(['{0}_med_h'.format(localness), '{0}_avg_h'.format(localness), '{0}_nonlocal_med_h'.format(localness),
                                  '{0}_nonlocal_avg_h'.format(localness), '{0}_local_included'.format(localness), '{0}_nonlocal_included'.format(localness),
                                  '{0}_local_excluded'.format(localness), '{0}_nonlocal_excluded'.format(localness)])
        csvwriter.writerow(output_header)
        for state in states:
            unfiltered_med_h = numpy.median(states[state]['{0}_local'.format(localness_metrics[0])] + states[state]['{0}_nonlocal'.format(localness_metrics[0])])
            unfiltered_avg_h = numpy.average(states[state]['{0}_local'.format(localness_metrics[0])] + states[state]['{0}_nonlocal'.format(localness_metrics[0])])
            output_row = [states[state]['fips'], unfiltered_med_h, unfiltered_avg_h]
            for localness in localness_metrics:
                local_med_h = numpy.median(states[state]['{0}_local'.format(localness)])
                local_avg_h = numpy.average(states[state]['{0}_local'.format(localness)])
                nonlocal_med_h = numpy.median(states[state]['{0}_nonlocal'.format(localness)])
                nonlocal_avg_h =  numpy.average(states[state]['{0}_nonlocal'.format(localness)])
                local_included = len(states[state]['{0}_local'.format(localness)])
                nonlocal_included = len(states[state]['{0}_nonlocal'.format(localness)])
                local_excluded = states[state]['{0}l_excluded'.format(localness)]
                nonlocal_excluded = states[state]['{0}n_excluded'.format(localness)]
                output_row.extend([local_med_h, local_avg_h, nonlocal_med_h, nonlocal_avg_h, local_included, nonlocal_included, local_excluded, nonlocal_excluded])
            csvwriter.writerow(output_row)


def update_localness_dict(states, n, p, v, l, state, havg):
    """
    Update happiness dictionary for a county/state with a tweet
    :param states: dictionary containing all results
    :param n: n-day local (bool)
    :param p: plurality local (bool)
    :param v: vgi median local (bool)
    :param l: location-field local (bool)
    :param state: FIPS code for state/county where the tweet is from
    :param havg: happiness for the tweet or None if no "happiness" words in tweet
    :return: no explicit return, dictionary is updated
    """
    local_results = {'n':n, 'p':p, 'v':v, 'l':l}
    if state not in states:
        states[state] = {'fips':state}
        for localness in localness_metrics:
            states[state]['{0}_local'.format(localness)] = []
            states[state]['{0}_nonlocal'.format(localness)] = []
            states[state]['{0}l_excluded'.format(localness)] = 0
            states[state]['{0}n_excluded'.format(localness)] = 0
    for localness in localness_metrics:
        if havg:
            if local_results[localness]:
                states[state]['{0}_local'.format(localness)].append(havg)
            else:
                states[state]['{0}_nonlocal'.format(localness)].append(havg)
        else:
            if local_results[localness]:
                states[state]['{0}l_excluded'.format(localness)] += 1
            else:
                states[state]['{0}n_excluded'.format(localness)] += 1


def build_happiness_dict():
    happiness_evaluations_fn = 'happiness/happiness_evaluations.txt'
    with open(happiness_evaluations_fn, 'r') as fin:
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


def main(scale='counties'):
    # generate word -> happiness dictionary
    happy_dict = build_happiness_dict()
    bots_filter = bots.build_bots_filter()

    tweets_dir = './happiness/distrib_p'  # './happiness/{0}'.format(scale)
    tweets_fns = os.listdir(tweets_dir)

    output_fn = "./happiness/happiness_by_{0}_bots_distrib_p.csv".format(scale)
    with open(output_fn, "w") as fout:
        csvwriter = csv.writer(fout)
        #for localness in ['nday','plurality','vgimed','locfield']:
        for localness in localness_metrics:
            csvwriter.writerow(['{0}_fips'.format(scale), '{0}_med_h'.format(localness), '{0}_avg_h'.format(localness), 'nonlocal_med_h', 'nonlocal_avg_h', 'unfiltered_med_h', 'unfiltered_avg_h', 'total_local', 'total_nonlocal', 'local_excluded', 'nonlocal_excluded'])
            local_filtered_out = 0
            nonlocal_filtered_out = 0
            for file in tweets_fns:
                with open(os.path.join(tweets_dir, file), 'r') as fin:
                    # print("Processing {0}".format(file))
                    fips = os.path.splitext(file)[0]
                    csvreader = csv.reader(fin)
                    #header = ['text','nday','plurality','vgimed','locfield']
                    header = ['text','uid','nday','plurality']
                    assert next(csvreader) == header
                    local_plur = []
                    lp_none = 0
                    non_local = []
                    nl_none = 0
                    for line in csvreader:
                        txt = line[header.index('text')]
                        uid = line[header.index('uid')]
                        if not line[header.index(localness)]:
                            continue
                        local = line[header.index(localness)] == 'True'
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
                                local_plur.append(h_avg_txt)
                            else:
                                non_local.append(h_avg_txt)
                        else:
                            if local:
                                lp_none += 1
                            else:
                                nl_none += 1

                    local_med_h = numpy.median(local_plur)
                    local_avg_h = numpy.average(local_plur)
                    nonlocal_med_h = numpy.median(non_local)
                    nonlocal_avg_h =  numpy.average(non_local)
                    unfiltered_med_h = numpy.median(local_plur + non_local)
                    unfiltered_avg_h = numpy.average(local_plur + non_local)
                    csvwriter.writerow([fips, local_med_h, local_avg_h, nonlocal_med_h, nonlocal_avg_h, unfiltered_med_h, unfiltered_avg_h, len(local_plur), len(non_local), lp_none, nl_none])
                    if False:
                        print("{0} local tweets, {1} nonlocal tweets, {2} local tweets excluded, {3} nonlocal tweets excluded".format(len(local_plur), len(non_local), lp_none, nl_none))
                        print("{0} local median happiness".format(local_med_h))
                        print("{0} local average happiness".format(local_avg_h))
                        print("{0} nonlocal median happiness".format(nonlocal_med_h))
                        print("{0} nonlocal average happiness".format(nonlocal_avg_h))
                        print("{0} unfiltered median happiness".format(unfiltered_med_h))
                        print("{0} unfiltered median happiness".format(unfiltered_avg_h))
            print("{0} 'local' tweets and {1} 'nonlocal' tweets filtered out from organizations for {2}.".format(local_filtered_out, nonlocal_filtered_out, localness))

    process_happiness_results(scale, output_fn)

if __name__ == "__main__":
    main('counties')
    #process_happiness_results('counties', "./happiness/happiness_by_counties_bots.csv")
