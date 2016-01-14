"""
Code largely taken from https://github.com/tapilab/twcounty/blob/master/twcounty/Demographics.ipynb.
A major thanks to Aron Culotta for posting his code and doing a fine job with it in the first place!
"""

# Classify users as male or female based on first names based on Census name frequency.
from collections import defaultdict
import re
import requests
import csv
import json
import os

def names_to_dict(url):
    """ Fetch data from census and parse into dict mapping name to frequency. """
    names = defaultdict(lambda: 0)
    for line in requests.get(url).text.split('\n'):
        parts = line.lower().split()
        if len(parts) >= 2:
            names[parts[0]] = float(parts[1])
    return names

def get_census_names():
    """ Fetch census name data and remove ambiguous names. """
    males = names_to_dict('http://www2.census.gov/topics/genealogy/1990surnames/dist.male.first')
    females = names_to_dict('http://www2.census.gov/topics/genealogy/1990surnames/dist.female.first')
    # print(len(set(list(males.keys()) + list(females.keys()))), 'total names')
    eps = 10.  # keep names that are eps times more frequent in one gender than the other.
    tokeep = []
    for name in set(list(males.keys()) + list(females.keys())):
        mscore = males[name]
        fscore = females[name]
        if mscore == 0 or fscore == 0 or mscore / fscore > eps or fscore / mscore > eps:
            tokeep.append(name)
    print(len(tokeep), 'names for gender determination.')
    m = set([n for n in tokeep if males[n] > females[n]])
    f = set([n for n in tokeep if females[n] > males[n]])
    return m, f

def get_census_race():
    pct_threshold = 90.0
    racefn = 'demographic_labeling/app_c.csv'
    surname_to_race = {}
    with open(racefn, 'r') as fin:
        csvreader = csv.reader(fin)
        # Fields:
        # last name, rank, # of people, per 100k people, cumulate per 100k people of line + higher ranking,
        #  % white non-hispanic, % black non-hispanic, % asian pacific-islander non-hispanic,
        #  % american indian alaskan native non-hispanic, % non-hispanic 2+ races, % hispanic
        assert next(csvreader) == ['name','rank','count','prop100k','cum_prop100k',
                                   'pctwhite','pctblack','pctapi','pctaian','pct2prace','pcthispanic']
        b = 0
        w = 0
        a = 0
        l = 0
        for line in csvreader:
            surname = line[0].lower()
            try:
                pctwhite = float(line[5])
            except:
                pctwhite = 0
            try:
                pctblack = float(line[6])
            except:
                pctblack = 0
            try:
                pctapi = float(line[7])
            except:
                pctapi = 0
            try:
                pcthispanic = float(line[8])
            except:
                pcthispanic = 0
            if pctwhite > pct_threshold:
                surname_to_race[surname] = 'w'
                w += 1
            elif pctblack > pct_threshold:
                surname_to_race[surname] = 'b'
                b += 1
            elif pctapi > pct_threshold:
                surname_to_race[surname] = 'a'
                a += 1
            elif pcthispanic > pct_threshold:
                surname_to_race[surname] = 'l'
                l += 1
    print("{0} names registered.".format(len(surname_to_race)))
    print("{0} white, {1} black, {2} asian, {3} latino".format(w,b,a,l))


    return surname_to_race

def label_gender(tweet, males, females):
    """ Classify a tweet as male (m) female (f) or neutral (n) based on first token in name field. """
    #name = tweet['user']['name'].lower().split()
    name = tweet.lower().split()
    if len(name) == 0:
        name = ['']
    name = re.findall('\w+', name[0])
    if len(name) == 0:
        name = ''
    else:
        name = name[0]
    if name in males:
        return 'm'
        tweet['user']['gender'] = 'm'
    elif name in females:
        return 'f'
        tweet['user']['gender'] = 'f'
    else:
        return 'n'
        tweet['user']['gender'] = 'n'
    return tweet


def update_tweetasjson():
    males, females = get_census_names()
    surnames_to_race = get_census_race()
    tweets_fn = "tweet_as_json.csv"
    output_fn = "tid_gender.csv"
    count_gender = 0
    count_race = 0
    total = 0
    with open(tweets_fn, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['tweet', 'tid', 'uid', 'lat', 'lon', 'county_fip']
        with open(output_fn, 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(['tid','gender','race'])
            for line in csvreader:
                tweet = json.loads(line[0])
                gender = label_gender(tweet, males, females)
                race = label_race_by_last_name(tweet, surnames_to_race)
                if gender != 'n':
                    count_gender += 1
                if race != 'n':
                    count_race += 1
                total += 1
                csvwriter.writerow([line[1], gender, race])
    print("{0} tweets processed, {1} labeled with a gender, and {2} labeled with a race.".format(total, count_gender, count_race))


def label_race_by_description(tweet):

    #desc = tweet['user']['description'].lower()
    desc = tweet.lower()
    if not desc:
        desc = ''
    toks = set(re.findall('\w+', desc.lower()))

    if len(set(['african', 'black', 'aa', 'sbm', 'sbf']) & toks) > 0:
        return 'b'
        tweet['user']['race'] = 'b'
    elif len(set(['latin', 'latino', 'latina', 'hispanic']) & toks) > 0:
        return 'l'
        tweet['user']['race'] = 'l'
    else:
        return 'n'
        tweet['user']['race'] = 'n'
    return tweet

def label_race_by_last_name(tweet, surname_to_race):

    #name = tweet['user']['name'].lower().split()
    name = tweet.lower().split()
    if len(name) < 2:
        name = ['','']
    name = re.findall('\w+', name[1])
    if len(name) == 0:
        name = ''
    else:
        name = name[0]
    if name in surname_to_race:
        return surname_to_race[name]
        tweet['user']['race'] = surname_to_race[name]
    else:
        return 'n'
        tweet['user']['race'] = 'n'
    return tweet

def main():
    males, females = get_census_names()
    surnames_to_race = get_census_race()

    rootdir = '.'
    tweet_files = []
    print("Tweet files from QUAC json2t[c]sv.")
    for dirName, subdirList, fileList in os.walk(rootdir):
        for fname in fileList:
            if fname.find(".all.csv") > -1:
                print(dirName + r'/' + fname)
                tweet_files.append(dirName + r'/' + fname)

    count_gen = 0
    count_race_surname = 0
    with open('tweet_as_json_demographics_counties.csv', 'w') as fout:
        csvwriter = csv.writer(fout)
        for file in tweet_files:
            with open(file, 'r') as fin:
                csvreader = csv.reader(fin)
                header = next(csvreader)
                header.extend(['gender', 'race'])
                for line in csvreader:
                    gender = label_gender(line[2], males, females)
                    if gender in ['m','f']:
                        count_gen += 1
                    raceSN = label_race_by_last_name(line[2], surnames_to_race)
                    if raceSN in ['b','l','w','a']:
                        count_race_surname += 1
                    line.extend([gender, raceSN])
                    csvwriter.writerow(line)

    print('{0} gender labeled and {1} race labeled by surname and {2} labeled by desc out of {3} records.'.format(count_gen, count_race_surname, count_race_desc, len(records)))


def testSF():
    males, females = get_census_names()
    surnames_to_race = get_census_race()
    sf_tweets_fn = 'output_data/06075_tweets.csv'
    records = []
    count_gen = 0
    count_race_desc = 0
    count_agree = 0
    count_race_surname = 0
    with open(sf_tweets_fn, 'r') as fin:
        csvreader = csv.reader(fin)
        header = next(csvreader)
        header.extend(['gender', 'race'])
        for line in csvreader:
            gender = label_gender(line[2], males, females)
            if gender in ['m','f']:
                count_gen += 1
            raceSN = label_race_by_last_name(line[2], surnames_to_race)
            raceD = label_race_by_description(line[3])
            if raceSN in ['b','l','w','a']:
                count_race_surname += 1
            if raceD in ['b','l']:
                count_race_desc += 1
                if raceSN != 'n' and raceD == raceSN:
                    count_agree += 1
            line.extend([gender, raceSN])
            records.append(line)
    with open(sf_tweets_fn.replace('.csv','_updated.csv'), 'w') as fout:
        csvwriter = csv.writer(fout)
        csvwriter.writerow(header)
        for record in records:
            csvwriter.writerow(record)

    print('{0} gender labeled and {1} race labeled by surname and {2} labeled by desc out of {3} records.'.format(count_gen, count_race_surname, count_race_desc, len(records)))


if __name__ == "__main__":
    main()
