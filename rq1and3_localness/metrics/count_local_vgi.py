import csv
import json
import argparse
import sys

sys.path.append*("./utils")
import bots

INPUT_HEADER = ['id', 'created_at', 'text', 'user_screen_name', 'user_description', 'user_lang', 'user_location',
                'user_time_zone', 'geom_src', 'uid', 'tweet', 'lon', 'lat', 'gender', 'race',
                'county', 'nday', 'plurality', 'geomed', 'locfield']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('localness_fn', help='CSV output from localness.py script')
    parser.add_argument('output_stats_fn', help="Path to CSV file output containing the localness stats by county")
    parser.add_argument('--filter_bots', default=True)
    args = parser.parse_args()

    localness_fn = args.localness_fn
    output_fn = args.output_stats_fn
    county_idx = INPUT_HEADER.index('county')
    uid_idx = INPUT_HEADER.index('uid')
    nday_idx = INPUT_HEADER.index("nday")
    plur_idx = INPUT_HEADER.index("plurality")
    geomed_idx = INPUT_HEADER.index("geomed")
    locfield_idx = INPUT_HEADER.index("locfield")
    twitter_bots = {}
    if args.filter_bots:
        twitter_bots = bots.build_bots_filter()

    print("Processing {0} and outputting localness results to {1}.".format(localness_fn, output_fn))
    output_header = ['fips','all','none','nday','plur','geomed','locfield','npg','ngl','npl','pgl','np','ng','nl','pg','pl','gl','bots']
    tracking = {'fips' : ""}
    for i in range(1, len(output_header)):
        tracking[output_header[i]] = 0

    county_stats = {}
    with open("resources/USCounties_bare.geojson",'r') as fin:
        counties = json.load(fin)

    for county in counties['features']:
        fips = str(county['properties']["FIPS"])
        county_stats[fips] = tracking.copy()
        county_stats[fips]['fips'] = fips

    with open(localness_fn, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == INPUT_HEADER
        line_no = 0
        for line in csvreader:
            line_no += 1
            fips = line[county_idx]
            uid = line[uid_idx]
            n, p, g, l = False, False, False, False
            if fips:
                if uid in twitter_bots:
                    county_stats[fips]['bots'] += 1
                    continue

                if line[nday_idx] == 'True':
                    n = True
                if line[plur_idx] == "True":
                    p = True
                if line[geomed_idx] == "True":
                    g = True
                if line[locfield_idx] == "True":
                    l = True

                if n and p and g and l:
                    county_stats[fips]['all'] += 1
                elif not n and not p and not g and not l:
                    county_stats[fips]['none'] += 1

                elif n and p and g:
                    county_stats[fips]['npg'] += 1
                elif n and g and l:
                    county_stats[fips]['ngl'] += 1
                elif n and p and l:
                    county_stats[fips]['npl'] += 1
                elif p and g and l:
                    county_stats[fips]['pgl'] += 1

                elif n and p:
                    county_stats[fips]['np'] += 1
                elif n and g:
                    county_stats[fips]['ng'] += 1
                elif n and l:
                    county_stats[fips]['nl'] += 1
                elif p and g:
                    county_stats[fips]['pg'] += 1
                elif p and l:
                    county_stats[fips]['pl'] += 1
                elif g and l:
                    county_stats[fips]['gl'] += 1

                elif n:
                    county_stats[fips]['nday'] += 1
                elif p:
                    county_stats[fips]['plur'] += 1
                elif g:
                    county_stats[fips]['geomed'] += 1
                elif l:
                    county_stats[fips]['locfield'] += 1

            if line_no % 100000 == 0:
                print('{0} lines processed.'.format(line_no))

    print('{0} total lines processed.'.format(line_no))
    with open(output_fn, "w") as fout:
        csvwriter = csv.DictWriter(fout, fieldnames=output_header)
        csvwriter.writeheader()
        for county in county_stats.values():
            csvwriter.writerow(county)


if __name__ == "__main__":
    main()