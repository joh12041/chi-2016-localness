import json
import csv
import argparse

from shapely.wkt import loads
from shapely.geometry import shape
from shapely.geometry import box


def main(geo_median=True, locfield=False, vgi_repository='t51m'):

    # some hacking to get the variables the way that I want them from command line or as called from another function
    if geo_median:
        POINTS_FN = 'geo_median/{0}/user_medians.csv'.format(vgi_repository)
        OUTPUT_FN = 'geo_median/{0}/user_counties.csv'.format(vgi_repository)
        EXPECTED_HEADER = ['uid', 'median']
        OUTPUT_HEADER = ['uid', 'county']
        PT_INDEX = 1
    elif locfield:
        POINTS_FN = 'location_field/{0}/user_points.csv'.format(vgi_repository)
        OUTPUT_FN = 'location_field/{0}/user_counties.csv'.format(vgi_repository)
        EXPECTED_HEADER = ['uid', 'loc_field', 'pt']
        OUTPUT_HEADER = ['uid', 'loc_field', 'county']
        PT_INDEX = 2
    parser = argparse.ArgumentParser()
    parser.add_argument('--points_fn', default=POINTS_FN)
    parser.add_argument('--output_fn', default=OUTPUT_FN)
    parser.add_argument('--expected_header', default=EXPECTED_HEADER)
    parser.add_argument('--output_header', default=OUTPUT_HEADER)
    parser.add_argument('--pt_index', default=PT_INDEX)
    parser.add_argument('--vgi_repository', default=vgi_repository)
    args = parser.parse_args()
    POINTS_FN = args.points_fn
    OUTPUT_FN = args.output_fn
    EXPECTED_HEADER = args.expected_header
    OUTPUT_HEADER = args.output_header
    PT_INDEX = args.pt_index

    counties_fn = 'resources/USCounties_bare.geojson'
    with open(counties_fn, 'r') as fin:
        counties_gj = json.load(fin)

    states_fn = 'resources/US_States_from_counties.geojson'
    with open(states_fn, 'r') as fin:
        states_gj = json.load(fin)

    counties = {}
    for state in states_gj['features']:
        west, south, east, north = shape(state['geometry']).bounds
        counties[state['properties']['FIPS'][:2]] = {'bb':box(west, south, east, north), 'counties':{}}
    for region in counties_gj['features']:
        state_fips = region['properties']['FIPS'][:2]
        counties[state_fips]['counties'][region['properties']['FIPS']] = shape(region['geometry'])
    del(counties_gj)
    del(states_gj)

    fast_lookup = {}

    eastUS = -66.885444
    westUS = -124.848974
    northUS = 49.384358
    southUS = 24.396308
    boundingboxUS = box(westUS, southUS, eastUS, northUS)

    with open(POINTS_FN, 'r') as fin:
        csvreader = csv.reader(fin)
        total_points = 0
        points_in_US = 0
        count_lines = 0
        assert next(csvreader) == EXPECTED_HEADER
        with open(OUTPUT_FN, 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(OUTPUT_HEADER)
            for line in csvreader:
                count_lines += 1
                uid = line[0]
                point = line[PT_INDEX]
                county = None
                try:
                    latlon = point[1:-1].split(',')
                    pt = loads('POINT ({0} {1})'.format(latlon[1].strip(), latlon[0].strip()))
                    total_points += 1
                    if line[PT_INDEX] in fast_lookup:
                        county = fast_lookup[line[PT_INDEX]]
                        points_in_US += 1
                    else:
                        if boundingboxUS.contains(pt):
                            for state in counties:
                                if counties[state]['bb'].contains(pt):
                                    for fips in counties[state]['counties']:
                                        if counties[state]['counties'][fips].contains(pt):
                                            county = fips
                                            points_in_US += 1
                                            fast_lookup[line[PT_INDEX]] = county
                                            break
                except Exception as e:
                    if line[PT_INDEX]:
                        print(e)
                        print(line)
                if geo_median:
                    csvwriter.writerow([uid, county])
                elif locfield:
                    csvwriter.writerow([uid, line[1], county])
                if total_points % 10000 == 0:
                    print ("{0} of {1} points in US and {2} lines in.".format(points_in_US, total_points, count_lines))
    print("{0} of {1} in the US out of {2} total lines.".format(points_in_US, total_points, count_lines))

if __name__ == "__main__":
    main()
