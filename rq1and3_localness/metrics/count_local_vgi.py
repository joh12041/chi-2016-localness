__author__ = 'isaac'

import csv
import json
import argparse
import os
import psycopg2
import psycopg2.extras

from utils import bots

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('localness_fn', default='output_data/swarm/swarm_checkins_localness.csv')
    parser.add_argument('output_folder', default='output_data/swarm')
    parser.add_argument('--filter_bots', default=True)
    args = parser.parse_args()
    localness_fn = args.localness_fn
    output_fn = os.path.join(args.output_folder, 'county_localness_stats.csv')
    twitter_bots = {}
    if 'swarm' in localness_fn:
        header = ['uid','tid','lat','lon','created_at','place_id','county','nday','plurality','vgimed','locfield']
        county_idx = header.index('county')
    elif 'combined' in localness_fn:
        header = ['uid','text','lon','lat','county','nday','plurality']
        county_idx = header.index('county')
        if args.filter_bots:
            twitter_bots = bots.build_bots_filter()
            output_fn = output_fn.replace("_stats.csv", "_stats_bots.csv")
    elif 'twitter' in localness_fn:
        header = ['id','created_at','text','user_screen_name','user_description','user_lang','user_location',
                  'user_time_zone','lon','lat','geom_src','county','gender','race','uid','tweet',
                  'nday','plurality','vgimed','locfield']
        county_idx = header.index('county')
        if args.filter_bots:
            twitter_bots = bots.build_bots_filter()
            output_fn = output_fn.replace("_stats.csv", "_stats_bots.csv")
    elif 'flickr100m' in localness_fn:
        header = ['id','uid','date_taken','user_tags','accuracy','is_video','lon','lat','nickname','county_fip','zh_prefecture','nday','plurality','vgimed','locfield']
        county_idx = header.index('county_fip')
    elif 'flickr09to12' in localness_fn:
        header = ['fid','uid','lat','lon','datetaken','accuracy','views','county_fip','nday','plurality','vgimed','locfield']
        county_idx = header.index('county_fip')
    else:
        raise Exception("Invalid localness file - must have swarm, twitter, flickr100m, or flickr09to12 in the name")
    uid_idx = header.index('uid')
    print("Processing {0} and outputting localness results to {1}.".format(localness_fn, output_fn))
    tracking = {
    'fips' : '',
    # Unambiguous
    'all' : 0,
    'none' : 0,

    # All but one True
    'npv' : 0,
    'nvl' : 0,
    'npl' : 0,
    'pvl' : 0,

    # Two True
    'np' : 0,
    'nv' : 0,
    'nl' : 0,
    'pv' : 0,
    'pl' : 0,
    'vl' : 0,

    # Only one True
    'nday' : 0,
    'plur' : 0,
    'vgi' : 0,
    'loc' : 0,

    'botGSM' : 0}

    line_no = 0

    county_stats = {}
    with open("geometries/USCounties_bare.geojson",'r') as fin:
        counties = json.load(fin)

    for county in counties['features']:
        fips = str(county['properties']["FIPS"])
        county_stats[fips] = tracking.copy()
        county_stats[fips]['fips'] = fips

    with open(localness_fn, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == header
        for line in csvreader:
            line_no += 1
            fips = line[county_idx]
            uid = line[uid_idx]
            n,p,v,l = False,False,False,False
            if fips:
                if uid in twitter_bots:
                    county_stats[fips]['botGSM'] += 1
                    continue
                if line[header.index('nday')] == 'True':
                    n = True
                if line[header.index('plurality')] == "True":
                    p = True
                if 'vgimed' in header and line[header.index('vgimed')] == "True":
                    v = True
                if 'locfield' in header and line[header.index('locfield')] == "True":
                    l = True

                if n and p and v and l:
                    county_stats[fips]['all'] += 1
                elif not n and not p and not v and not l:
                    county_stats[fips]['none'] += 1

                elif n and p and v:
                    county_stats[fips]['npv'] += 1
                elif n and v and l:
                    county_stats[fips]['nvl'] += 1
                elif n and p and l:
                    county_stats[fips]['npl'] += 1
                elif p and v and l:
                    county_stats[fips]['pvl'] += 1

                elif n and p:
                    county_stats[fips]['np'] += 1
                elif n and v:
                    county_stats[fips]['nv'] += 1
                elif n and l:
                    county_stats[fips]['nl'] += 1
                elif p and v:
                    county_stats[fips]['pv'] += 1
                elif p and l:
                    county_stats[fips]['pl'] += 1
                elif v and l:
                    county_stats[fips]['vl'] += 1

                elif n:
                    county_stats[fips]['nday'] += 1
                elif p:
                    county_stats[fips]['plur'] += 1
                elif v:
                    county_stats[fips]['vgi'] += 1
                elif l:
                    county_stats[fips]['loc'] += 1

            if line_no % 20000 == 0:
                print('{0} lines processed.'.format(line_no))

    print('{0} total lines processed.'.format(line_no))
    with open(output_fn, "w") as fout:
        csvwriter = csv.DictWriter(fout, fieldnames=list(tracking.keys()))
        csvwriter.writeheader()
        for county in county_stats.values():
            csvwriter.writerow(county)

def compare_datasets():

    conn = psycopg2.connect("dbname=twitterstream_zh_us")
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
    NDAY_MIN = 10

    for repository in [['flickr100m','flickr09to12'], ['twitter14','twitter15']]:
        if 'flickr' in repository[0]:
            bot_users = {}
        else:
            bot_users = bots.build_bots_filter()
        cur.execute("SELECT uid, county_fip, cnt, ntime FROM ndaytemp_{0};".format(repository[0]))
        print("Processing nday and plurality for {0}...".format(repository[0]))
        user_counties = {repository[0]:{}, repository[1]:{}}
        for row in cur:
            uid = str(row[0])
            if uid in bot_users:
                continue
            county = row[1]  # string
            count_VGI = row[2]  # int
            ntime = row[3]  # PostgreSQL interval converted to datetime.timedelta by psycopg2
            if uid in user_counties[repository[0]]:
                user_counties[repository[0]][uid][county] = [ntime.days >= NDAY_MIN, count_VGI]
                if count_VGI > user_counties[repository[0]][uid]['plurality_count']:
                    user_counties[repository[0]][uid]['plurality'] = [county]
                    user_counties[repository[0]][uid]['plurality_count'] = count_VGI
                elif count_VGI == user_counties[repository[0]][uid]['plurality_count']:
                    user_counties[repository[0]][uid]['plurality'].append(county)
            else:
                user_counties[repository[0]][uid] = {county : [ntime.days >= NDAY_MIN, count_VGI], 'plurality' : [county], 'plurality_count': count_VGI}

        for user in user_counties[repository[0]]:
            if user_counties[repository[0]][user]['plurality_count'] == 1 and len(user_counties[repository[0]][user]['plurality']) == 1:
                user_counties[repository[0]][user] = {'plurality':user_counties[repository[0]][user]['plurality'], 'plurality_count':user_counties[repository[0]][user]['plurality_count']}

        cur.execute("SELECT uid, county_fip, cnt, ntime FROM ndaytemp_{0};".format(repository[1]))
        print("Processing nday and plurality for {0}...".format(repository[1]))
        users_in_common = set()
        for row in cur:
            uid = str(row[0])
            if uid in bot_users:
                continue
            county = row[1]  # string
            count_VGI = row[2]  # int
            ntime = row[3]  # PostgreSQL interval converted to datetime.timedelta by psycopg2
            if uid in user_counties[repository[0]]:
                users_in_common.add(uid)
            if uid in user_counties[repository[1]]:
                user_counties[repository[1]][uid][county] = [ntime.days >= NDAY_MIN, count_VGI]
                if count_VGI > user_counties[repository[1]][uid]['plurality_count']:
                    user_counties[repository[1]][uid]['plurality'] = [county]
                    user_counties[repository[1]][uid]['plurality_count'] = count_VGI
                elif count_VGI == user_counties[repository[1]][uid]['plurality_count']:
                    user_counties[repository[1]][uid]['plurality'].append(county)
            else:
                user_counties[repository[1]][uid] = {county : [ntime.days >= NDAY_MIN, count_VGI], 'plurality' : [county], 'plurality_count': count_VGI}

        for user in user_counties[repository[1]]:
            if user_counties[repository[1]][user]['plurality_count'] == 1 and len(user_counties[repository[1]][user]['plurality']) == 1:
                user_counties[repository[1]][user] = {'plurality':user_counties[repository[1]][user]['plurality'], 'plurality_count':user_counties[repository[1]][user]['plurality_count']}

        print("{0} users in common, {1} users in {2}, {3} users in {4}.".format(len(users_in_common), len(user_counties[repository[0]]), repository[0], len(user_counties[repository[1]]), repository[1]))
        nday_shared = 0
        nday_neither = 0
        nday_first_only = 0
        nday_second_only = 0
        nday_disagreed = 0
        plurality_agreed = 0
        plurality_vgi_agreed = 0
        plurality_vgi_disagreed = 0
        plurality_agreed_breakdown = {}
        plurality_disagreed_breakdown = {}
        vgi_agreed = 0
        vgi_agreed_no = 0
        vgi_disagreed = 0
        vgi_counties_only_one = 0
        for uid in users_in_common:
            p1 = user_counties[repository[0]][uid]['plurality']
            p2 = user_counties[repository[1]][uid]['plurality']
            if p1 == p2 or p1[0] in p2 or p2[0] in p1:
                plurality_agreed += 1
                plurality_vgi_agreed += user_counties[repository[0]][uid]['plurality_count'] + user_counties[repository[1]][uid]['plurality_count']
            else:
                plurality_vgi_disagreed += user_counties[repository[0]][uid]['plurality_count'] + user_counties[repository[1]][uid]['plurality_count']
            del(user_counties[repository[0]][uid]['plurality'])
            del(user_counties[repository[1]][uid]['plurality'])
            del(user_counties[repository[0]][uid]['plurality_count'])
            del(user_counties[repository[1]][uid]['plurality_count'])
            for fips in user_counties[repository[0]][uid]:
                if user_counties[repository[0]][uid][fips][0]:
                    if fips in user_counties[repository[1]][uid]:
                        if user_counties[repository[1]][uid][fips][0]:
                            nday_shared += 1
                            vgi_agreed += user_counties[repository[0]][uid][fips][1]
                            vgi_agreed += user_counties[repository[1]][uid][fips][1]
                            if 'twitter' in repository[0]:
                                mn = min(user_counties[repository[0]][uid][fips][1], user_counties[repository[1]][uid][fips][1])
                                mx = max(user_counties[repository[0]][uid][fips][1], user_counties[repository[1]][uid][fips][1])
                                if (mn, mx) in plurality_agreed_breakdown:
                                    plurality_agreed_breakdown[(mn, mx)] += 1
                                else:
                                    plurality_agreed_breakdown[(mn, mx)] = 1
                        else:
                            nday_disagreed += 1
                            vgi_disagreed += user_counties[repository[0]][uid][fips][1]
                            vgi_disagreed += user_counties[repository[1]][uid][fips][1]
                            if 'twitter' in repository[0]:
                                mn = min(user_counties[repository[0]][uid][fips][1], user_counties[repository[1]][uid][fips][1])
                                mx = max(user_counties[repository[0]][uid][fips][1], user_counties[repository[1]][uid][fips][1])
                                if (mn, mx) in plurality_disagreed_breakdown:
                                    plurality_disagreed_breakdown[(mn, mx)] += 1
                                else:
                                    plurality_disagreed_breakdown[(mn, mx)] = 1
                    else:
                        nday_first_only += 1
                        vgi_counties_only_one += user_counties[repository[0]][uid][fips][1]
                else:
                    if fips in user_counties[repository[1]][uid] and not user_counties[repository[1]][uid][fips]:
                        nday_neither += 1
                        vgi_agreed_no += user_counties[repository[0]][uid][fips][1]
                        vgi_agreed_no += user_counties[repository[1]][uid][fips][1]
            for fips in user_counties[repository[1]][uid]:
                if user_counties[repository[1]][uid][fips]:
                    if fips in user_counties[repository[0]][uid]:
                        if user_counties[repository[0]][uid][fips]:
                            continue  # already marked above
                        else:
                            nday_disagreed += 1
                    else:
                        nday_second_only += 1

        print("{0} counties shared (nday), {1} no in both, {2} counties disagreed, {3} counties in {4} only, and {5} counties in {6} only".format(nday_shared, nday_neither, nday_disagreed, nday_first_only, repository[0], nday_second_only, repository[1]))
        print("{0} contributions in the counties agreed over and {1} contributions in the counties disagreed about".format(vgi_agreed, vgi_disagreed))
        print("{0} users plurality had overlap out of {1} users.".format(plurality_agreed, len(users_in_common)))
        print("{0} contributions in agreement, {1} contributions in disagreement".format(plurality_vgi_agreed, plurality_vgi_disagreed))

        if 'twitter' in repository:
            with open('plurality_agreed.csv', 'w') as fout:
                csvwriter = csv.writer(fout)
                csvwriter.writerow(['pair','count'])
                for pair in plurality_agreed_breakdown:
                    csvwriter.writerow([pair, plurality_agreed_breakdown[pair]])
            with open('plurality_disagreed.csv', 'w') as fout:
                csvwriter = csv.writer(fout)
                csvwriter.writerow(['pair','count'])
                for pair in plurality_disagreed_breakdown:
                    csvwriter.writerow([pair, plurality_disagreed_breakdown[pair]])


        print("Processing VGI median results...")
        vgi_median_file = "vgi_median/{0}/user_counties.csv".format(repository[0])
        medians = {}
        with open(vgi_median_file, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == ['uid', 'county']
            count_median_first = 0
            count_nomedian_first = 0
            for line in csvreader:
                uid = line[0]
                if uid in bot_users:
                    continue
                county = line[1]
                if county:
                    count_median_first += 1
                    medians[uid] = county
                else:
                    count_nomedian_first += 1
                    medians[uid] = False
        print('{0} medians added for {1} and {2} without a county.'.format(count_median_first, repository[0], count_nomedian_first))

        vgi_median_file = "vgi_median/{0}/user_counties.csv".format(repository[1])
        with open(vgi_median_file, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == ['uid', 'county']
            count_median_second = 0
            count_nomedian_second = 0
            users_in_common = 0
            medians_in_common = 0
            medians_disagreed = 0
            medians_first_only = 0
            medians_second_only = 0
            medians_neither = 0
            for line in csvreader:
                uid = line[0]
                if uid in bot_users:
                    continue
                county = line[1]
                if uid in medians:
                    users_in_common += 1
                    if county and medians[uid] == county:
                        medians_in_common += 1
                        count_median_second += 1
                    elif county and medians[uid]:
                        medians_disagreed += 1
                        count_median_second += 1
                    elif medians[uid]:
                        medians_first_only += 1
                        count_nomedian_second += 1
                    elif county:
                        medians_second_only += 1
                        count_median_second += 1
                    else:
                        medians_neither += 1
                        count_nomedian_second += 1
                else:
                    if county:
                        count_median_second += 1
                    else:
                        count_nomedian_second += 1

        print('{0} medians added for {1} and {2} without a county.'.format(count_median_second, repository[1], count_nomedian_second))
        print("Out of {0} users in common: {1} medians in common, {2} medians disagreed, {3} in {4} only, {5} in {6} only, and {7} in neither.".format(
            users_in_common, medians_in_common, medians_disagreed, medians_first_only, repository[0], medians_second_only, repository[1], medians_neither))


        # map's users to their location field data pulled from the Flickr API
        print("Processing location field results...")
        location_field_file = "location_field/{0}/user_counties_cleaned.csv".format(repository[0])
        locations = {}
        with open(location_field_file, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == ['uid', 'loc_field', 'county']
            for line in csvreader:
                uid = line[0]
                county = line[2].split(';')  # in case multiple counties (e.g., NYC)
                locations[uid] = county
        print("{0} locations registered for {1}.".format(len(locations), repository[0]))

        location_field_file = "location_field/{0}/user_counties_cleaned.csv".format(repository[1])
        locfield_in_common = set()
        locfield_agreed = 0
        locfield_disagreed = 0
        locfield_first_only = 0
        locfield_second_only = 0
        locfield_neither = 0
        with open(location_field_file, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == ['uid', 'loc_field', 'county']
            for line in csvreader:
                uid = line[0]
                county = line[2].split(';')  # in case multiple counties (e.g., NYC)
                if uid in locations:
                    locfield_in_common.add(uid)
                    if locations[uid] == county:
                        locfield_agreed += 1
                    elif locations[uid] and county:
                        locfield_disagreed += 1
                    elif locations[uid]:
                        locfield_first_only += 1
                    elif county:
                        locfield_second_only += 1
                    else:
                        locfield_neither += 1

        print('{0} users in both files with {1} in common, {2} disagreed, {3} in {4} only, {5} in {6} only, and {7} in neither.'.format(
            len(locfield_in_common), locfield_agreed, locfield_disagreed, locfield_first_only, repository[0], locfield_second_only, repository[1], locfield_neither))


if __name__ == "__main__":
    compare_datasets()