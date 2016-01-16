import os
import csv

def build_bots_filter():
    """
    Build dictionary for fast-lookup of all Twitter userIDs determined to be of organizations
    :return: dictionary of userID strings - presence in the dictionary = organization
    """
    bot_users = {}  # dict for quick lookup
    bots_folders = ['../humanizr/results/t51m', '../humanizr/results/t11m']
    for folder in bots_folders:
        bots_fn = os.listdir(folder)
        for file in bots_fn:
            with open(os.path.join(folder, file), 'r') as fin:
                csvreader = csv.reader(fin, delimiter="\t")
                # header = ['uid','label']  # label can be 'org' for organization or 'per' for person
                for line in csvreader:
                    uid = line[0]
                    label = line[1]
                    if label == 'org':
                        bot_users[uid] = True

    print("{0} users who are bots.".format(len(bot_users)))
    return bot_users