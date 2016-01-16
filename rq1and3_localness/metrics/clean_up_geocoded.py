import csv

def main(vgi_repository='t51m', points=True):
    filter_out = {}  # dict for fast look-up
    with open("location_field/state_table.csv", "r") as fin:
        csvreader = csv.reader(fin)
        next(csvreader)
        for line in csvreader:
            if line[1] != 'Washington DC':
                for direction in ['', 'southern ', 'eastern ', 'northern ', 'central ', 'western ']:
                    filter_out[direction + line[1].lower()] = True  # e.g. Alabama
                    filter_out[direction + line[2].lower()] = True  # e.g. AL
                    filter_out[direction + line[1].lower() + ", usa"] = True
                    filter_out[direction + line[2].lower() + ", usa"] = True
                    filter_out[direction + line[1].lower() + ", us"] = True
                    filter_out[direction + line[2].lower() + ", us"] = True

    filter_out['america'] = True
    filter_out['etats-unis'] = True
    filter_out['usa'] = True
    filter_out['u.s.a.'] = True
    filter_out['us'] = True
    filter_out['u.s.'] = True
    filter_out['united states'] = True
    filter_out['united states of america'] = True
    filter_out['estados unidos'] = True

    filter_out['pacific northwest'] = True
    filter_out['the mitten'] = True
    filter_out['tejas'] = True
    filter_out['new england'] = True
    filter_out['lone star state'] = True

    filter_out['earth'] = True
    filter_out['nowhere'] = True
    filter_out['arg'] = True
    filter_out['central city'] = True
    filter_out['location'] = True
    filter_out['disney'] = True
    filter_out['clouds'] = True
    filter_out['area 51'] = True
    filter_out['westside'] = True
    filter_out['lol'] = True
    filter_out['house'] = True
    filter_out['krypton'] = True
    filter_out['pandora'] = True
    filter_out['cosmos'] = True
    filter_out['beach'] = True
    filter_out['happy'] = True
    filter_out['mars'] = True
    filter_out['bed'] = True
    filter_out['wonderland'] = True
    filter_out['south'] = True
    filter_out['nirvana'] = True
    filter_out['bdg'] = True
    filter_out['life'] = True
    filter_out['heart'] = True
    filter_out['indian'] = True
    filter_out['eastern'] = True
    filter_out['mlk'] = True
    filter_out['hope'] = True

    filter_out['badlands'] = True
    filter_out['dixie'] = True
    filter_out['san andreas'] = True
    filter_out['transylvania'] = True
    filter_out['belgique'] = True
    filter_out['pateros'] = True  # Manila
    filter_out['corsica'] = True
    filter_out['wimbledon'] = True
    filter_out['fsu'] = True
    filter_out['scandinavia'] = True
    filter_out['mhs'] = True
    filter_out['queen city'] = True # likely Cincinnati but a general term too...
    filter_out['ayrshire'] = True
    filter_out['alberta'] = True
    filter_out['newfoundland'] = True
    filter_out['bromley'] = True  # district in London

    with open('location_field/country_codes.tsv', 'r') as fin:
        csvreader = csv.reader(fin, delimiter='\t')
        header = next(csvreader)
        country_idx = header.index('Country')
        for line in csvreader:
            country = line[country_idx].lower().strip()
            filter_out[country] = True

    fix = {}
    if points:
        fix['washington dc'] = '(38.89511, -77.03637)'
        fix['twin cities, mn'] = '(44.96219, -93.178555)'  # Average of Minneaplis center and St. Paul center
        fix['twin cities, minnesota'] = '(44.96219, -93.178555)'
        fix['city of angels'] = '(34.05223, -118.24368)'
        fix['the city of angels'] = '(34.05223, -118.24368)'
        fix['phil'] = "(39.95233, -75.16379)"
        fix['delco'] = "(39.9168, -75.3989)"
        fix['steel city'] = "(40.44062, -79.99589)"
        fix['queens'] = "(40.76538, -73.81736)"
        for nyc_variant in ['nyc', 'new york, new york','new york city', 'new york, ny', 'ny, ny', 'the big apple']:
            fix[nyc_variant] = '(40.78343, -73.96625)'

    else:
        fix['washington dc'] = '11001'
        fix['twin cities, mn'] = '27053;27123'
        fix['twin cities, minnesota'] = '27053;27123'
        fix['city of angels'] = '06037'
        fix['the city of angels'] = '06037'
        fix['phil'] = '42101'
        fix['delco'] = '42045'
        fix['steel city'] = '42003'
        fix['queens'] = '36081'
        for nyc_variant in ['nyc', 'new york, new york','new york city', 'new york, ny', 'ny, ny', 'the big apple']:
           fix[nyc_variant] = '36047;36061;36081;36085;36005'

    updated = 0
    filtered_out = 0
    locfields_removed = {}
    if points:
        input_fn = "./{0}/user_points.csv".format(vgi_repository)
    else:
        input_fn = "./{0}/user_counties.csv".format(vgi_repository)
    with open(input_fn, "r") as fin:
        csvreader = csv.reader(fin)
        with open(input_fn.replace(".csv","_cleaned.csv"), "w") as fout:
            csvwriter = csv.writer(fout)
            for line in csvreader:
                if line[1] and line[1].lower().strip() in filter_out:
                    csvwriter.writerow([line[0], line[1], None])
                    if line[1].lower().strip() in locfields_removed:
                        locfields_removed[line[1].lower().strip()] += 1
                    else:
                        locfields_removed[line[1].lower().strip()] = 1
                    filtered_out += 1
                elif line[1].lower().strip() in fix:
                    csvwriter.writerow([line[0], line[1], fix[line[1].lower().strip()]])
                    updated += 1
                else:
                    csvwriter.writerow(line)

    for locfield in locfields_removed:
        print(locfield, locfields_removed[locfield])
    print("{0} updated and {1} filtered out.".format(updated, filtered_out))

if __name__ == "__main__":
    main()