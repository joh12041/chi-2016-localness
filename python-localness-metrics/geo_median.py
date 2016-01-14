__author__ = 'joh12041'

# Code largely taken from: https://gist.github.com/endolith/2837160
#  with some help from https://github.com/ahwolf/meetup_location/blob/master/code/geo_median.py
#  and adapted to support great circle distances over Euclidean.

from geopy.distance import vincenty
from geopy.distance import great_circle
import csv
import numpy
from collections import OrderedDict
import traceback
import json
from shapely.wkt import loads
from shapely.geometry import shape

VGI_REPOSITORY = 'twitter15'
LIMIT_MAD = 30  # acceptable km limit to median absolute deviation of points
LIMIT_POINTS = 5  # acceptable minimum number of GPS points for a user
DISTANCE_THRESHOLD = 1  # distance (meters) between iterations that determines end of search
DATA_POINTS_FILE = 'vgi_median/{0}/user_points.csv'.format(VGI_REPOSITORY)
OUTPUT_MEDIANS = 'vgi_median/{0}/user_medians.csv'.format(VGI_REPOSITORY)
SNAP_TO_USER_POINTS = False
OUTPUT_ALL_USERS = True

def main():
    #compute_user_median([(40.641975,-73.791994),(25.079263,121.23692),(40.727037,-73.98385),(40.642,-73.792),(40.642,-73.792),(25.077265,121.234934),(25.077464,121.235185)],10000, None, None)
    compute_medians()

def compute_medians(suffix='', iterations=1000, already_computed=None):

    numIter = iterations  # numIter depends on how long it take to get a suitable convergence of objFunc
    count = 0

    if suffix:
        infn = DATA_POINTS_FILE.replace(".csv", "_" + suffix + ".csv")
        outfn = OUTPUT_MEDIANS.replace(".csv", "_" + suffix + ".csv")
    else:
        infn = DATA_POINTS_FILE
        outfn = OUTPUT_MEDIANS

    already_computed_users = {}
    if already_computed:
        for file in already_computed:
            with open(file, 'r') as fin:
                csvreader = csv.reader(fin)
                assert next(csvreader) == ['uid', 'median']
                for line in csvreader:
                    already_computed_users[line[0]] = True

    with open(infn, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['uid','lat','lon']
        with open(outfn, 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(['uid','median'])
            line = next(csvreader)
            dataPoints = [(float(line[1]), float(line[2]))]
            current_uid = line[0]
            for line in csvreader:
                if line[0] == current_uid:
                    dataPoints.append((float(line[1]), float(line[2])))
                else:
                    count += 1
                    if count % 2500 == 0:
                        print("Processed {0} users.".format(count))

                    if current_uid not in already_computed_users:
                        compute_user_median(dataPoints, numIter, csvwriter, current_uid)

                    # set user and restart array for new current user
                    current_uid = line[0]
                    dataPoints = [(float(line[1]), float(line[2]))]
            compute_user_median(dataPoints, numIter, csvwriter, current_uid)

def candMedian(dataPoints):
    #Calculate the first candidate median as the geometric mean
    tempLat = 0.0
    tempLon = 0.0

    for i in range(0, len(dataPoints)):
        tempLat += dataPoints[i][0]
        tempLon += dataPoints[i][1]

    return (tempLat / len(dataPoints), tempLon / len(dataPoints))

def checkMedianAbsoluteDeviation(dataPoints, median):
    # Calculate Median Absolute Deviation of a set of points
    distances = []
    for i in range(0, len(dataPoints)):
        try:
            distances.append(vincenty(median, dataPoints[i]).kilometers)
        except ValueError:
            # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
            distances.append(great_circle(median, dataPoints[i]).kilometers)
    return(numpy.median(distances))

def numersum(testMedian, dataPoint):
    # Provides the denominator of the weiszfeld algorithm depending on whether you are adjusting the candidate x or y
    try:
        return 1 / vincenty(testMedian, dataPoint).kilometers
    except ZeroDivisionError:
        traceback.print_exc()
        return 0  # filter points that equal the median out (otherwise no convergence)
    except ValueError:
        # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
        return 1 / great_circle(testMedian, dataPoint).kilometers

def denomsum(testMedian, dataPoints):
    # Provides the denominator of the weiszfeld algorithm
    temp = 0.0
    for i in range(0, len(dataPoints)):
        try:
            temp += 1 / vincenty(testMedian, dataPoints[i]).kilometers
        except ZeroDivisionError:
            print('zerodivisionerror', dataPoints[i])
            continue  # filter points that equal the median out (otherwise no convergence)
        except ValueError:
            # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
            temp += 1 / great_circle(testMedian, dataPoints[i]).kilometers
    return temp

def objfunc(testMedian, dataPoints):
    # This function calculates the sum of linear distances from the current candidate median to all points
    # in the data set, as such it is the objective function that we are minimising.
    temp = 0.0
    for i in range(0, len(dataPoints)):
        try:
            temp += vincenty(testMedian, dataPoints[i]).kilometers
        except ValueError:
            # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
            temp += great_circle(testMedian, dataPoints[i]).kilometers
    return temp

def compute_user_median(dataPoints, numIter, csvwriter, current_uid):
    if len(dataPoints) < LIMIT_POINTS:  # Insufficient points for the user - don't record median
        if OUTPUT_ALL_USERS:
            csvwriter.writerow([current_uid, None])
    else:
        if SNAP_TO_USER_POINTS: # ensure median is one of the user's points
            lowestDev = float("inf")
            for point in dataPoints:
                tmpAbsDev = objfunc(point, dataPoints)
                if tmpAbsDev < lowestDev:
                    lowestDev = tmpAbsDev
                    testMedian = point
        else:
            testMedian = candMedian(dataPoints)  # Calculate centroid more or less as starting point
            if objfunc(testMedian, dataPoints) != 0:  # points aren't all the same

                #iterate to find reasonable estimate of median
                for x in range(0, numIter):
                    denom = denomsum(testMedian, dataPoints)
                    nextLat = 0.0
                    nextLon = 0.0

                    for y in range(0, len(dataPoints)):
                        nextLat += (dataPoints[y][0] * numersum(testMedian, dataPoints[y]))/denom
                        nextLon += (dataPoints[y][1] * numersum(testMedian, dataPoints[y]))/denom

                    prevMedian = testMedian
                    testMedian = (nextLat, nextLon)
                    try:
                        if vincenty(prevMedian, testMedian).meters < DISTANCE_THRESHOLD:  # 1 meter
                            break
                    except:
                        if great_circle(prevMedian, testMedian).meters < DISTANCE_THRESHOLD:  # 1 meter
                            break

                if x == numIter - 1:
                    print('{0}: failed to converge. Last change between iterations was {1} meters.'.format(current_uid, great_circle(prevMedian, testMedian).meters))

        # Check if user points are under the limit median absolute deviation
        if checkMedianAbsoluteDeviation(dataPoints, testMedian) <= LIMIT_MAD:
            csvwriter.writerow([current_uid, (round(testMedian[0],6), round(testMedian[1],6))])
        else:
            if OUTPUT_ALL_USERS:
                csvwriter.writerow([current_uid, None])

def recheck_nonconvergers(fn='vgi_median/{0}/logfile.txt'.format(VGI_REPOSITORY)):
    # users = {'2904745915':True}  # didn't get processed first time for Twitter because at end of file and that was a bug
    users = {}
    suffix = "second_iter"
    with open(fn, 'r') as fin:
        for line in fin:
            try:
                line = line.split(': ')
                users[line[0]] = True
            except:
                print('Failed to process:', line)

    with open(DATA_POINTS_FILE, 'r') as fin:
        csvreader = csv.reader(fin)
        outfn = DATA_POINTS_FILE.replace(".csv", "_" + suffix + ".csv")
        with open(outfn, 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(['uid','lat','lon'])
            for line in csvreader:
                if line[0] in users:
                    csvwriter.writerow(line)

    print('{0} users to process on the this iteration.'.format(len(users)))
    compute_medians(suffix, 10000)

def combine_median_files():
    suffix = 'second_iter'
    first = OUTPUT_MEDIANS
    overwrite = OUTPUT_MEDIANS.replace(".csv", "_" + suffix + ".csv")
    final = OUTPUT_MEDIANS.replace(".csv", "_aggregated.csv")
    header = ['uid', 'median']

    points = OrderedDict()

    for filenm in [first, overwrite]:
        countlines = 0
        with open(filenm, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == header
            for line in csvreader:
                countlines += 1
                uid = line[0]
                median = line[1]
                points[uid] = median
            print(filenm, countlines)
    with open(final, 'w') as fout:
        countlines = 0
        csvwriter = csv.writer(fout)
        csvwriter.writerow(header)
        for user in points:
            countlines += 1
            csvwriter.writerow([user, points[user]])
        print(final, countlines)

def process_users_points_for_states(dataPoints, states, csvwriter, current_uid):
    prev_state = '01'  # Most likely state to contain the point is the state containing the previous point
    user_states = set()
    for pt in dataPoints:
        if states[prev_state].contains(loads('POINT ({0} {1})'.format(pt[1], pt[2]))):
            user_states.add(prev_state)
        else:
            for state in states:
                if states[state].contains(loads('POINT ({0} {1})'.format(pt[1], pt[2]))):
                    user_states.add(state)
                    prev_state = state
                    break
    csvwriter.writerow([current_uid, len(user_states)])

def count_states():
    states_geojson_fn = 'geometries/USStates.geojson'
    with open(states_geojson_fn, 'r') as fin:
        states_gj = json.load(fin)
    states = {}
    for state in states_gj['features']:
        states[state['properties']['FIPS'][:2]] = shape(state['geometry'])
    del(states_gj)

    count = 0
    with open(DATA_POINTS_FILE, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['uid','lat','lon']
        with open('wikipedia_editor_state_counts.csv', 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(['uid','median'])
            line = next(csvreader)
            dataPoints = [(float(line[1]), float(line[2]))]
            current_uid = line[0]
            for line in csvreader:
                if line[0] == current_uid:
                    dataPoints.append((float(line[1]), float(line[2])))
                else:
                    count += 1
                    if count % 2500 == 0:
                        print("Processed {0} users.".format(count))

                    process_users_points_for_states(dataPoints, states, csvwriter, current_uid)

                    # set user and restart array for new current user
                    current_uid = line[0]
                    dataPoints = [(float(line[1]), float(line[2]))]
            process_users_points_for_states(dataPoints, states, csvwriter, current_uid)

if __name__ == "__main__":
    main()
