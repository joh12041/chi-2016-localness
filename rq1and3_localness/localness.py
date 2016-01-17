import csv
import traceback
import json
import sys

import psycopg2
import psycopg2.extras
from shapely.wkt import loads
from shapely.geometry import shape
from shapely.geometry import box

sys.path.append("./utils")
import demographic_labeling

COUNT_GEOTAGGED = 0

# should be "counties" and 5 or "states" and 2
SCALE = "counties"
FIPS_LENGTH = 5

DB_NAME = "<PSQL DB NAME>"
NDAY_TABLE_NAME = "<PSQL TABLE NAME>"
NDAY_MIN = 10  # minimum span of days between first and last VGI for a county to be counted as local

GEOMED_RESULTS_FN = "<FILE PATH TO GEOMED RESULTS CSV>"
LOCFIELD_RESULTS_FN = "<FILE PATH TO LOCFIELD RESULTS CSV>"

INPUT_FN = "<FILE PATH TO INPUT VGI DATA CSV>"
INPUT_HAS_HEADER = False
# INPUT_COLUMNS should match columns in input CSV
# If county has been precomputed, then it should be part of INPUT_COLUMNS
# EXTEND_COLUMNS are the additional columns to be computed. Gender/race are optional.
INPUT_COLUMNS = ['tweet']
EXTEND_COLUMNS = ['gender', 'race', 'county', 'nday', 'plurality', 'geomed', 'locfield']
OUTPUT_COLUMNS = INPUT_COLUMNS + EXTEND_COLUMNS
OUTPUT_FN = "<FILE PATH TO OUTPUT VGI DATA WITH LOCALNESS INFO APPENDED CSV>"

COMPUTE_COUNTY_FROM_LAT_LON = True
COMPUTE_DEMOGRAPHICS = True

def get_county(counties, pt):
    global COUNT_GEOTAGGED
    for state in counties:
        if counties[state]['bb'].contains(pt):
            for fips in counties[state]['counties']:
                if counties[state]['counties'][fips].contains(pt):
                    COUNT_GEOTAGGED += 1
                    return fips
    return None

def print_progress(line_number, count_failed, count_processed, count_gender, count_race, loc_failed):
    print("{0} lines read in, {1} processed fully, {2} location field lookups failed, and {3} failed for other reasons."
          "and {3} total written out to {4}.".format(line_number, count_processed, loc_failed, count_failed))
    print("{0} gender determined and {1} race determined.".format(count_gender, count_race))
    print("{0} located in the US.".format(COUNT_GEOTAGGED))

def main():

    conn = psycopg2.connect("dbname={0}".format(DB_NAME))
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

    print("Querying database for nday/plurality results...")
    # SQL: CREATE TABLE <TABLENAME> (uid bigint, fips char(5), count int, ntime interval);
    cur.execute("SELECT uid, fips, count, ntime FROM {0};".format(NDAY_TABLE_NAME))

    print("Processing nday and plurality...")
    user_regions = {}
    for row in cur:
        uid = str(row[0])  # bigint -> string
        region = row[1]
        if region:
            region = region[:FIPS_LENGTH]  # string
        count_VGI = row[2]  # int
        ntime = row[3]  # PostgreSQL interval converted to datetime.timedelta by psycopg2
        if uid in user_regions:
            user_regions[uid][region] = (ntime.days >= NDAY_MIN)
            if count_VGI > user_regions[uid]['plurality_count']:
                user_regions[uid]['plurality'] = [region]
                user_regions[uid]['plurality_count'] = count_VGI
            elif count_VGI == user_regions[uid]['plurality_count']:
                user_regions[uid]['plurality'].append(region)
        else:
            user_regions[uid] = {region : ntime.days >= NDAY_MIN, 'plurality' : [region], 'plurality_count': count_VGI}
    print("{0} users processed.".format(len(user_regions)))

    print("Processing VGI geometric median results...")
    with open(GEOMED_RESULTS_FN, 'r') as fin:
        csvreader = csv.reader(fin)
        # assert next(csvreader) == ['uid', 'county']
        count_vgimed = 0
        for line in csvreader:
            uid = line[0]
            region = line[1][:FIPS_LENGTH]
            try:
                if region:
                    count_vgimed += 1
                    user_regions[uid]['median'] = region
                elif uid in user_regions:
                    user_regions[uid]['median'] = False
            except KeyError as e:
                print(e, line)
                continue
    print("{0} VGI medians added.".format(count_vgimed))

    # Ignore user data because some users posted multiple locations so not all uids have a unique entry
    print("Processing location field results...")
    locations = {}
    with open(LOCFIELD_RESULTS_FN, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['uid', 'loc_field', 'county']
        for line in csvreader:
            loc_field = line[1]
            region = line[2].split(';')  # in case multiple counties (e.g., NYC)
            for i in range(0, len(region)):
                region[i] = region[i][:FIPS_LENGTH]
            locations[loc_field] = region
    print("{0} locations registered.".format(len(locations)))

    print("Now to process localness!")
    line_number = 0
    count_processed = 0
    count_failed = 0
    loc_failed = 0
    count_gender = 0
    count_race = 0

    if COMPUTE_DEMOGRAPHICS:
        gender_idx = OUTPUT_COLUMNS.index('gender')
        race_idx = OUTPUT_COLUMNS.index('race')
        males, females = demographic_labeling.get_census_names()
        surnames_to_race = demographic_labeling.get_census_race()

    if COMPUTE_COUNTY_FROM_LAT_LON:
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

    with open(OUTPUT_FN, 'w') as fout:
        csvwriter = csv.writer(fout)
        csvwriter.writerow(OUTPUT_COLUMNS)
        with open(INPUT_FN, 'r') as fin:
            csvreader = csv.reader(fin)
            try:
                tweet_idx = OUTPUT_COLUMNS.index('tweet')
            except ValueError:
                tweet_idx = -1
            # alternatively replace the user_location_idx with the tweet if you have that full object and adjust code
            #  to pull location field entry from tweet json object
            county_idx = OUTPUT_COLUMNS.index('county')
            nday_idx = OUTPUT_COLUMNS.index('nday')
            plur_idx = OUTPUT_COLUMNS.index('plurality')
            geomed_idx = OUTPUT_COLUMNS.index('geomed')
            locfield_idx = OUTPUT_COLUMNS.index('locfield')
            default_extend_columns = [False for i in range(0, len(EXTEND_COLUMNS))]
            if INPUT_HAS_HEADER:
                assert next(csvreader) == INPUT_COLUMNS
            for record in csvreader:
                line_number += 1
                try:
                    tweet = json.loads(record[tweet_idx])
                    uid = str(tweet['user']['id'])
                    record.extend(default_extend_columns)  # NOTE: using extend means that a copy is inserted

                    if COMPUTE_COUNTY_FROM_LAT_LON
                        if tweet['geo']:  # has coordinates
                            pt = loads('POINT ({0} {1})'.format(
                                    tweet['geo']['coordinates'][1], tweet['geo']['coordinates'][0]))
                            region = get_county(counties, pt)
                        else:
                            region = None
                    else:
                        region = record[county_idx]
                    if region:
                        region = region[:FIPS_LENGTH]
                    record[county_idx] = region  # output file will reflect state or county scale

                    if COMPUTE_DEMOGRAPHICS:
                        gender = demographic_labeling.label_gender(tweet, males, females)
                        if gender != 'n':
                            count_gender += 1
                        race = demographic_labeling.label_race_by_last_name(tweet, surnames_to_race)
                        if race != 'n':
                            count_race += 1
                        record[gender_idx] = gender
                        record[race_idx] = race

                    # Skip localness metric checks if no county (i.e., tweet isn't geotagged or is outside of US).
                    if region:
                        # n-day
                        if user_regions[uid][region]:
                            record[nday_idx] = True
                        # plurality
                        if region in user_regions[uid]['plurality']:
                            record[plur_idx] = True
                        # geometric median
                        if region == user_regions[uid]['median']:
                            record[geomed_idx] = True
                        # location field
                        try:
                            loc_field_entry = tweet['user']['location']
                            # location not found - make sure isn't a unicode issue
                            if loc_field_entry and loc_field_entry not in locations:
                                loc_field_entry = loc_field_entry.encode().decode('unicode-escape')
                            # self-reported location exists and matches county of VGI
                            if loc_field_entry and region in locations[loc_field_entry]:
                                record[locfield_idx] = True
                        except Exception:
                            loc_failed += 1
                            print("Lookup Failed:", loc_field_entry)
                    csvwriter.writerow(record)
                    count_processed += 1
                except Exception as e:
                    count_failed += 1
                    print(e)
                    print(record)
                    traceback.print_exc()
                if line_number % 100000 == 0:
                    print_progress(line_number, count_failed, count_processed, count_gender, count_race, loc_failed)
            print_progress(line_number, count_failed, count_processed, count_gender, count_race, loc_failed)
            print("VGI read in from {0} and output to {1}.".format(INPUT_FN, OUTPUT_FN))


if __name__ == "__main__":
    main()