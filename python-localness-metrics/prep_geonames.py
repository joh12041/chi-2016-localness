__author__ = 'isaac'

import csv
import json
from shapely.geometry import shape

ADMIN1_FN = "location_field/admin1CodesASCII.txt"
COUNTIES_GEOJSON = "geometries/USCounties_bare.geojson"
CITIES1000_FN = "location_field/cities1000.txt"  # for a smaller geocoder with only cities of 1000 people and up + admin capitols
CITIES_FN = "location_field/allCountries.txt"  # larger geocoder - any place labeled a city regardless of population
COUNTRIES_FN = "location_field/country_codes.tsv"
GEONAMES_PARSED_FN = "location_field/geonames_countries.tsv"
#GEONAMES_PARSED_FN = "location_field/geonames_countries_GlobalJake.tsv"
COUNT_AMBIGUOUS = 0
DELIMITER=','

def add_place(geocoder_dict, place, lat, lon, pop):
    global COUNT_AMBIGUOUS
    if place in geocoder_dict:
        COUNT_AMBIGUOUS += 1
        if geocoder_dict[place][2] < pop:  # existing entry has a smaller population so replace
            geocoder_dict[place] = (lat, lon, pop)
    else:
        geocoder_dict[place] = (lat, lon, pop)

def remove_place(geocoder_dict, place):
    if place in geocoder_dict:
        del(geocoder_dict[place])
        print('{0} deleted.'.format(place))
    else:
        print('{0} not in dict to be deleted.'.format(place))

def main():

    countries = {}
    with open(COUNTRIES_FN, 'r') as fin:
        csvreader = csv.reader(fin, delimiter='\t')
        for line in csvreader:
            try:
                code = line[0].lower()
                name = line[4].lower()
                countries[code] = name
            except Exception as e:
                print(e)
                print(line)

    regions = {}
    with open(ADMIN1_FN, 'r') as fin:
        csvreader = csv.reader(fin, delimiter='\t')
        for line in csvreader:
            try:
                code = line[0].lower()
                name = line[1].lower()
                regions[code] = name
            except Exception as e:
                print(e)
                print(line)

    with open(CITIES_FN, 'r') as fin:
        csvreader = csv.reader(fin, delimiter="\t", quoting=csv.QUOTE_NONE)
        geonames = {}
        count = 0
        for line in csvreader:
            #if line[6] != "U":
            if line[6] == 'P':  # remove this line if using cities1000.txt
                count += 1
                try:
                    names = []
                    names.append(line[1].replace('"','').lower())
                    for alt_name in set(line[3].split(',')):
                        alt_name = alt_name.replace('"','').lower()
                        if alt_name != names[0] and alt_name:
                            names.append(alt_name)
                    if line[8] and line[10] and line[10] != '00':  # 8 = Country Code, 10 = Admin1 (State) Code, 10 == '00' means general feature in multiple states
                        try:
                            region_name = regions[(line[8] + "." + line[10]).lower()]
                        except:
                            print(line[8] + "." + line[10])
                            region_name = None
                    else:
                        region_name = None
                    country_name = countries[line[8].lower()]
                    lat = line[4]
                    lon = line[5]
                    try:
                        pop = int(line[14])
                    except:
                        pop = -1

                    for city_name in names:
                        if city_name and region_name and country_name:
                            city_region_country = city_name+DELIMITER+region_name+DELIMITER+country_name
                            city_region = city_name+DELIMITER+region_name
                            city_country = city_name+DELIMITER+country_name
                            add_place(geonames, city_region_country, lat, lon, pop)
                            add_place(geonames, city_region, lat, lon, pop)
                            add_place(geonames, city_country, lat, lon, pop)

                        elif city_name and region_name:
                            city_region = city_name+DELIMITER+region_name
                            add_place(geonames, city_region, lat, lon, pop)

                        elif city_name and country_name:
                            if city_name != country_name:
                                city_country = city_name+DELIMITER+country_name
                                add_place(geonames, city_country, lat, lon, pop)

                        add_place(geonames, city_name, lat, lon, pop)
                        if count % 100000 == 0:
                            print("{0} processed.".format(count))

                except Exception as e:
                    print(e)
                    print(line)

    print("Ambiguous Filtered Out:", COUNT_AMBIGUOUS)
    print("Total Unique Entries:", len(geonames))
    length_without_admin2 = len(geonames)

    county_counts = {}
    with open(COUNTIES_GEOJSON, 'r') as fin:
        counties = json.load(fin)

        for county in counties['features']:
            try:
                county['centroid'] = shape(county['geometry']).centroid
                state = county['properties']['StateName']
                county_name = county['properties']['CountyName']
                county_state = county_name + DELIMITER + state
                if county_state in geonames:
                    print("ERROR: {0} should not appear more than once!".format(county_state))
                geonames[county_state] = (county['centroid'].y, county['centroid'].x)
                if county_name in county_counts:
                    county_counts[county_name]['count'] += 1
                else:
                    county_counts[county_name] = {'count':1, 'lat_lon': (county['centroid'].y, county['centroid'].x)}
            except Exception as e:
                print(e)
                print(line)
        for county in county_counts:
            if county_counts[county]['count'] == 1:
                if county not in geonames:
                    geonames[county] = county_counts[county]['lat_lon']
                else:
                    print("I'm surprised that {0} already exists...".format(county))

    print("{0} counties added.".format(len(geonames) - length_without_admin2))

    with open(GEONAMES_PARSED_FN, 'w') as fout:
        csvwriter = csv.writer(fout, delimiter="\t")
        csvwriter.writerow(['place', 'lat', 'lon'])
        for place in geonames:
            csvwriter.writerow([place, geonames[place][0], geonames[place][1]])


if __name__ == "__main__":
    main()
