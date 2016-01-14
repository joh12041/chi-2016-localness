__author__ = 'joh12041'

import psycopg2
import psycopg2.extras
import csv
import traceback
import json
import os
from shapely.wkt import loads
from shapely.geometry import shape
from shapely.geometry import box
from demographic_labeling import demographic_labeling

COUNT_GEOTAGGED = 0

def get_county(counties, pt):
    global COUNT_GEOTAGGED
    for state in counties:
        if counties[state]['bb'].contains(pt):
            for fips in counties[state]['counties']:
                if counties[state]['counties'][fips].contains(pt):
                    COUNT_GEOTAGGED += 1
                    return fips
    return None

def main():

    VGI_REPOSITORY = 'twitter15'
    conn = psycopg2.connect("dbname=twitterstream_zh_us")
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

    NDAY_MIN = 10  # days

    vgi_median_file = "vgi_median/{0}/user_counties.csv".format(VGI_REPOSITORY)
    location_field_file = "location_field/{0}/user_counties_cleaned.csv".format(VGI_REPOSITORY)
    preserve_columns = ['id', 'created_at', 'text', 'user_screen_name', 'user_description','user_lang','user_location',
                            'user_time_zone','lon', 'lat', 'geom_src','county','gender', 'race', 'uid', 'tweet',
                            'nday', 'plurality', 'vgimed', 'locfield']

    print("Querying database for nday/plurality results...")
    cur.execute("SELECT uid, county_fip, cnt, ntime FROM ndaytemp_{0};".format(VGI_REPOSITORY))

    print("Processing nday and plurality...")
    user_counties = {}
    for row in cur:
        uid = str(row[0])
        county = row[1]  # string
        count_VGI = row[2]  # int
        ntime = row[3]  # PostgreSQL interval converted to datetime.timedelta by psycopg2
        if uid in user_counties:
            user_counties[uid][county] = ntime.days >= NDAY_MIN
            if count_VGI > user_counties[uid]['plurality_count']:
                user_counties[uid]['plurality'] = [county]
                user_counties[uid]['plurality_count'] = count_VGI
            elif count_VGI == user_counties[uid]['plurality_count']:
                user_counties[uid]['plurality'].append(county)
        else:
            user_counties[uid] = {county : ntime.days >= NDAY_MIN, 'plurality' : [county], 'plurality_count': count_VGI}
    print("{0} users processed.".format(len(user_counties)))

    print("Processing VGI median results...")
    with open(vgi_median_file, 'r') as fin:
        csvreader = csv.reader(fin)
        # assert next(csvreader) == ['uid', 'county']
        count_vgimed = 0
        for line in csvreader:
            uid = str(line[0])
            county = line[1]
            try:
                if county:
                    count_vgimed += 1
                    user_counties[uid]['median'] = county
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
            locations[loc_field] = county
    print("{0} locations registered.".format(len(locations)))

    print("Now to process {0}...".format(VGI_REPOSITORY))
    count_failed = 0
    loc_failed = 0
    count_processed = 0
    count_gender = 0
    count_race = 0
    if 'twitter' in VGI_REPOSITORY:
        all_VGI_fn = []
        output_allVGIfn = '{0}_localness.csv'.format(VGI_REPOSITORY)
        rootdir = '.'
        for dirName, subdirList, fileList in os.walk(rootdir):
            for fname in fileList:
                if fname.find(".all.csv") > -1:
                    print(dirName + r'/' + fname)
                    all_VGI_fn.append(dirName + r'/' + fname)
        lat_idx = preserve_columns.index('lat')
        lon_idex = preserve_columns.index('lon')
        gender_idx = preserve_columns.index('gender')
        race_idx = preserve_columns.index('race')

        counties_fn = 'geometries/USCounties_bare.geojson'
        with open(counties_fn, 'r') as fin:
            counties_gj = json.load(fin)

        states_fn = 'geometries/US_States_from_counties.geojson'
        with open(states_fn, 'r') as fin:
            states_gj = json.load(fin)

        counties = {}
        for state in states_gj['features']:
            west, south, east, north = shape(state['geometry']).bounds
            counties[state['properties']['FIPS'][:2]] = {'bb':box(west, south, east, north), 'counties':{}}
        for county in counties_gj['features']:
            state_fips = county['properties']['FIPS'][:2]
            counties[state_fips]['counties'][county['properties']['FIPS']] = shape(county['geometry'])
        del(counties_gj)
        del(states_gj)

        males, females = demographic_labeling.getCensusNames()
        surnames_to_race = demographic_labeling.getCensusRace()

    with open(output_allVGIfn, 'w') as fout:
        csvwriter = csv.writer(fout)
        csvwriter.writerow(preserve_columns)
        for file in all_VGI_fn:
            with open(file, 'r') as fin:
                csvreader = csv.reader(fin)
                # assert next(csvreader) == preserve_columns[:-4]
                for record in csvreader:
                    try:
                        uid = record[preserve_columns.index('uid')]
                        if 'twitter' in VGI_REPOSITORY and record[lon_idex]:  # Twitter + has coordinates
                            pt = loads('POINT ({0} {1})'.format(record[lon_idex], record[lat_idx]))
                            county = get_county(counties, pt)
                            record[preserve_columns.index('county')] = county
                        else:
                            county = record[preserve_columns.index('county')]
                        if 'twitter' in VGI_REPOSITORY:  # demographic labeling
                            gender = demographic_labeling.labelGender(record[gender_idx], males, females)
                            if gender != 'n':
                                count_gender += 1
                            race = demographic_labeling.labelRacebyLastName(record[race_idx], surnames_to_race)
                            if race != 'n':
                                count_race += 1
                            record[gender_idx] = gender
                            record[race_idx] = race
                        if county:
                            if user_counties[uid][county]:  # n-day
                                record.append(True)
                            else:
                                record.append(False)
                            if county in user_counties[uid]['plurality']:  # plurality
                                record.append(True)
                            else:
                                record.append(False)
                            if county == user_counties[uid]['median']:  # vgi median
                                record.append(True)
                            else:
                                record.append(False)
                            try:
                                loc_field_entry = json.loads(record[preserve_columns.index('tweet')])['user']['location']
                                if loc_field_entry and loc_field_entry not in locations:
                                    loc_field_entry = loc_field_entry.encode().decode('unicode-escape')
                                if loc_field_entry and county in locations[loc_field_entry]:  # self-reported location
                                    record.append(True)
                                else:
                                    record.append(False)
                            except Exception:
                                loc_failed += 1
                                print("Lookup Failed:", loc_field_entry)
                                record.append(False)
                        else:
                            record.extend([False, False, False, False])
                        csvwriter.writerow(record)
                        count_processed += 1
                    except Exception as e:
                        count_failed += 1
                        print(e)
                        print(record)
                        traceback.print_exc()
            print("Complete with {0}. {1} total location lookups failed, {2} total failed for other reasons, and {3} total written out to {4}.".format(file, loc_failed, count_failed, count_processed, output_allVGIfn))
            print("{0} gender determined and {1} race determined.".format(count_gender, count_race))
            print("{0} located in the US.".format(COUNT_GEOTAGGED))



if __name__ == "__main__":
    main()