"""
Code largely taken from https://github.com/tapilab/twcounty/blob/master/twcounty/Demographics.ipynb.
A major thanks to Aron Culotta for posting his code and doing a fine job with it in the first place!
"""

import csv
import re
from collections import defaultdict
import requests

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
    """ Fetch census race data and remove ambiguous names. """
    pct_threshold = 90.0
    racefn = 'demographic_labeling/app_c.csv'
    surname_to_race = {}
    with open(racefn, 'r') as fin:
        csvreader = csv.reader(fin)
        # Fields:
        # last name, rank, # of people, per 100k people, cumulate per 100k people of line + higher ranking,
        #  % white non-hispanic, % black non-hispanic, % asian pacific-islander non-hispanic,
        #  % american indian alaskan native non-hispanic, % non-hispanic 2+ races, % hispanic
        assert next(csvreader) == ['name', 'rank', 'count', 'prop100k', 'cum_prop100k',
                                   'pctwhite', 'pctblack', 'pctapi', 'pctaian', 'pct2prace', 'pcthispanic']
        b = 0
        w = 0
        a = 0
        l = 0
        for line in csvreader:
            surname = line[0].lower()
            try:
                pctwhite = float(line[5])
            except ValueError:
                pctwhite = 0
            try:
                pctblack = float(line[6])
            except ValueError:
                pctblack = 0
            try:
                pctapi = float(line[7])
            except ValueError:
                pctapi = 0
            try:
                pcthispanic = float(line[8])
            except ValueError:
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
    print("{0} white, {1} black, {2} asian, {3} latino".format(w, b, a, l))

    return surname_to_race

def label_gender(tweet, males, females):
    """ Classify a tweet as male (m) female (f) or neutral (n) based on first token in name field. """
    name = tweet['user']['name'].lower().split()
    if len(name) == 0:
        name = ['']
    name = re.findall('\w+', name[0])
    if len(name) == 0:
        name = ''
    else:
        name = name[0]
    if name in males:
        tweet['user']['gender'] = 'm'
    elif name in females:
        tweet['user']['gender'] = 'f'
    else:
        tweet['user']['gender'] = 'n'

    return tweet


def label_race_by_last_name(tweet, surname_to_race):
    """ Classify a tweet as white, black, asian, latino, or unknown based on second token in name field. """
    name = tweet['user']['name'].lower().split()
    if len(name) < 2:
        name = ['', '']
    name = re.findall('\w+', name[1])
    if len(name) == 0:
        name = ''
    else:
        name = name[0]
    if name in surname_to_race:
        tweet['user']['race'] = surname_to_race[name]
    else:
        tweet['user']['race'] = 'n'

    return tweet
