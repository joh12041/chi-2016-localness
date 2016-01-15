import csv

import psycopg2
import psycopg2.extras

from ..utils import bots

DBNAME = "<postgres-dbname>"
VGI_REPOSITORIES = ['t51m', 't11m', 'f15m', 's8m']
NDAY_TABLE_BASENAME = "nday_"
GEOMETRIC_MEDIAN_FOLDER = "geo_median"
GEOMETRIC_MEDIAN_FILENAME = "user_counties.csv"
LOCATION_FIELD_FOLDER = "location_field"
LOCATION_FIELD_FILENAME = "user_counties_cleaned.csv"

def main():
    """Generate stats on localness metric performance.

    Expects tables in a PostgreSQL database containing n-day information for each user.
    Plurality can be generated from the n-day data.
    Expects a CSV file with geometric median results for all of the users.
    Expects a CSV file with locaiton field results for all of the users.

    :return: prints out a lot of different stats about the localness metrics and their overlap
    """

    conn = psycopg2.connect("dbname={0}".format(DBNAME))
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
    results = [['repository','Users (K)','% 5-D','%10-D', '%30-D', '%60-D', '% Med', '% Loc', '',
                    '# VGI (M)', '% 5-D','%10-D','%30-D','%60-D', '% Plu', '% Med', '% Loc']]

    twitter_bots = bots.build_bots_filter()

    for repository in VGI_REPOSITORIES:
        cur.execute("SELECT uid, ntime, count, fips FROM {0}{1};".format(NDAY_TABLE_BASENAME, repository))
        users = {}  # keep track of the users who have been processed
        nday_localized_users_60 = set()  # number of users who are local to at least one county when n=60 days
        nday_localized_users_30 = set()
        nday_localized_users_10 = set()
        nday_localized_users_5 = set()
        nday_local_content_60 = 0  # number of VGI that are local when n=60 days
        nday_local_content_30 = 0
        nday_local_content_10 = 0
        nday_local_content_5 = 0
        nday_not_potentially_local_content = 0  # number of VGI that couldn't be local under n-days because user only contributed to once
        total_content = 0  # total number of VGI geolocated to counties
        users_plurality = {}  # track county with most contributions for each user
        users_content = {}  # track total amount of content per user for later stats in geometric median and location field
        for row in cur:
            uid = str(row[0])  # user ID
            if uid in twitter_bots:
                continue
            # ntime is a PostgreSQL interval converted to datetime.timedelta by psycopg2
            #  it's the time between first and last contributions to this county by the user
            ntime = row[1]
            cnt = row[2]  # number of VGI contributed to the county by the user
            county_fip = row[3]  # FIPS code for the county
            if county_fip:
                users[uid] = True
                total_content += cnt
                if ntime.days >= 60:
                    nday_localized_users_60.add(uid)
                    nday_local_content_60 += cnt
                if ntime.days >= 30:
                    nday_localized_users_30.add(uid)
                    nday_local_content_30 += cnt
                if ntime.days >= 10:
                    nday_localized_users_10.add(uid)
                    nday_local_content_10 += cnt
                if ntime.days >= 5:
                    nday_localized_users_5.add(uid)
                    nday_local_content_5 += cnt
                if uid in users_plurality:
                    if cnt > users_plurality[uid]['plurality_count']:  # new plurality county
                        users_plurality[uid]['plurality'] = [county_fip]
                        users_plurality[uid]['plurality_count'] = cnt
                    elif cnt == users_plurality[uid]['plurality_count']:  # tie: plurality assigned to all counties with that # of VGI
                        users_plurality[uid]['plurality'].append(county_fip)
                    users_content[uid][county_fip] = cnt
                else:
                    users_plurality[uid] = {'plurality':[county_fip], 'plurality_count':cnt}
                    users_content[uid] = {county_fip:cnt}

        plurality_local_content = 0
        for uid in users_plurality:
            # only one contribution for a user = couldn't be n-day and I want to track that
            if users_plurality[uid]['plurality_count'] == 1 and len(users_plurality[uid]['plurality']) == 1:
                nday_not_potentially_local_content += 1
            plurality_local_content += users_plurality[uid]['plurality_count'] * len(users_plurality[uid]['plurality'])

        print("{0}: {1} Total VGI and {2} users who only had one piece of VGI.".format(repository, total_content, nday_not_potentially_local_content))
        print("60-day: {0} users processed and {1} had at least one county determined to be local for {2}.".format(len(users), len(nday_localized_users_60), repository))
        print("30-day: {0} users processed and {1} had at least one county determined to be local for {2}.".format(len(users), len(nday_localized_users_30), repository))
        print("10-day: {0} users processed and {1} had at least one county determined to be local for {2}.".format(len(users), len(nday_localized_users_10), repository))
        print(" 5-day: {0} users processed and {1} had at least one county determined to be local for {2}.".format(len(users), len(nday_localized_users_5), repository))

        vgi_median_fn = '{0}/{1}/{2}'.format(GEOMETRIC_MEDIAN_FOLDER, repository, GEOMETRIC_MEDIAN_FILENAME)
        median_localized_users = 0  # number of users who were assigned a county per geometric median
        median_users_in_nday = 0  # number of users who overlap with ndays userlist (geometric median might include users without US points
        median_additional_users = 0  # number of users in geometric median who aren't in n-days
        median_local_content = 0  # number of VGI that were local to the geometric median county
        median_potentially_local_content = 0  # number of VGI produced by the localized users
        median_users_nocontent = 0  # number of users who didn't contribute to their geometric median county
        with open(vgi_median_fn, 'r') as fin:
            csvreader = csv.reader(fin)
            #assert next(csvreader) == ['uid','county']
            for line in csvreader:
                uid = line[0]
                if uid in twitter_bots:
                    continue
                county = line[1]
                if uid in users:
                    median_users_in_nday += 1
                    if county:
                        for fips in users_content[uid]:
                            median_potentially_local_content += users_content[uid][fips]
                        median_localized_users += 1
                        if county in users_content[uid]:
                            median_local_content += users_content[uid][county]
                        else:
                            median_users_nocontent += 1
                else:
                    median_additional_users += 1
        print("VGI Median: {0} users found from nday of which {1} were localized and {2} additional users not considered for {3}.".format(median_users_in_nday, median_localized_users, median_additional_users, repository))
        print("{0} VGI Median users with no content in the county where they are local.".format(median_users_nocontent))
        print("Out of {0} VGI that could have been declared local (i.e. vgi median was successful for that user), {1} was local.".format(median_potentially_local_content, median_local_content))

        locfield_fn = '{0}/{1}/'.format(LOCATION_FIELD_FOLDER, repository, LOCATION_FIELD_FILENAME)
        locfield_localized_users = set()
        locfield_users_in_nday = 0
        locfield_additional_users = 0
        locfield_local_content = 0
        locfield_potentially_local_content = 0
        locfield_users_nocontent = set()
        with open(locfield_fn, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == ['uid','loc_field','county']
            for line in csvreader:
                uid = line[0]
                if uid in twitter_bots:
                    continue
                counties = line[2].split(';')  # usually one county, but sometimes multiple as for NYC or Twin Cities
                if uid in users:
                    locfield_users_in_nday += 1
                    for county in counties:
                        if county:
                            for fips in users_content[uid]:
                                locfield_potentially_local_content += users_content[uid][fips]
                            locfield_localized_users.add(uid)
                            if county in users_content[uid]:
                                locfield_local_content += users_content[uid][county]
                            else:
                                locfield_users_nocontent.add(uid)
                else:
                    locfield_additional_users += 1
        print("LocField: {0} users found from nday of which {1} were localized and {2} additional users not considered for {3}.".format(locfield_users_in_nday, len(locfield_localized_users), locfield_additional_users, repository))
        print("{0} LocField users with no content in the county where they are local.".format(len(locfield_users_nocontent)))
        print("Out of {0} VGI that could have been declared local (i.e. loc field was successful for that user), {1} was local.".format(locfield_potentially_local_content, locfield_local_content))


        if repository == 'swarm':
            repository = 'swarm\t'  # prints out prettier in standard out
        results.append([repository,
                        round(len(users) / 1000.0, 1),
                        '',  # placeholder for better spacing of print
                        round(float(len(nday_localized_users_5)) / (len(users) - nday_not_potentially_local_content), 3),
                        round(float(len(nday_localized_users_10)) / (len(users) - nday_not_potentially_local_content), 3),
                        round(float(len(nday_localized_users_30)) / (len(users) - nday_not_potentially_local_content), 3),
                        round(float(len(nday_localized_users_60)) / (len(users) - nday_not_potentially_local_content), 3),
                        round(float(median_localized_users) / median_users_in_nday, 3),
                        round(float(len(locfield_localized_users)) / locfield_users_in_nday, 3),
                        '',
                        round(float(total_content) / 1000000.0, 1),
                        '',
                        round(float(nday_local_content_5) / (total_content - nday_not_potentially_local_content), 3),
                        round(float(nday_local_content_10) / (total_content - nday_not_potentially_local_content), 3),
                        round(float(nday_local_content_30) / (total_content - nday_not_potentially_local_content), 3),
                        round(float(nday_local_content_60) / (total_content - nday_not_potentially_local_content), 3),
                        round(float(plurality_local_content) / total_content, 3),
                        round(float(median_local_content) / median_potentially_local_content, 3),
                        round(float(locfield_local_content) / locfield_potentially_local_content, 3)])
    print('\n')
    for result in results:
        print('\t'.join(str(r) for r in result))

if __name__ == "__main__":
    main()