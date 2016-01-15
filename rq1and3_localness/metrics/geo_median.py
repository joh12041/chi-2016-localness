# Code largely taken from: https://gist.github.com/endolith/2837160
#  with some help from https://github.com/ahwolf/meetup_location/blob/master/code/geo_median.py
#  and adapted to support great circle distances over Euclidean.

import csv

from geopy.distance import vincenty
from geopy.distance import great_circle
import numpy

VGI_REPOSITORY = 't51m'
LIMIT_MAD = 30  # acceptable km limit to median absolute deviation of points
LIMIT_POINTS = 5  # acceptable minimum number of GPS points for a user
DISTANCE_THRESHOLD = 1  # distance (meters) between iterations that determines end of search
DATA_POINTS_FILE = 'geo_median/{0}/user_points.csv'.format(VGI_REPOSITORY)
OUTPUT_MEDIANS = 'geo_median/{0}/user_medians.csv'.format(VGI_REPOSITORY)
SNAP_TO_USER_POINTS = False
OUTPUT_ALL_USERS = True


def cand_median(dataPoints):
    """Calculate the first candidate median as the geometric mean."""
    tempLat = 0.0
    tempLon = 0.0

    for i in range(0, len(dataPoints)):
        tempLat += dataPoints[i][0]
        tempLon += dataPoints[i][1]

    return (tempLat / len(dataPoints), tempLon / len(dataPoints))

def check_median_absolute_deviation(data_points, median):
    """Calculate Median Absolute Deviation of a set of points."""
    distances = []
    for i in range(0, len(data_points)):
        try:
            distances.append(vincenty(median, data_points[i]).kilometers)
        except ValueError:
            # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
            distances.append(great_circle(median, data_points[i]).kilometers)
    return(numpy.median(distances))


def compute_user_median(data_points, num_iter, csvwriter, current_uid):
    if len(data_points) < LIMIT_POINTS:  # Insufficient points for the user - don't record median
        if OUTPUT_ALL_USERS:
            csvwriter.writerow([current_uid, None])
    else:
        if SNAP_TO_USER_POINTS: # ensure median is one of the user's points
            lowest_dev = float("inf")
            for point in data_points:
                tmp_abs_dev = objfunc(point, data_points)
                if tmp_abs_dev < lowest_dev:
                    lowest_dev = tmp_abs_dev
                    test_median = point
        else:
            test_median = cand_median(data_points)  # Calculate centroid more or less as starting point
            if objfunc(test_median, data_points) != 0:  # points aren't all the same
                # iterate to find reasonable estimate of median
                for x in range(0, num_iter):
                    denom = denomsum(test_median, data_points)
                    next_lat = 0.0
                    next_lon = 0.0

                    for y in range(0, len(data_points)):
                        next_lat += (data_points[y][0] * numersum(test_median, data_points[y])) / denom
                        next_lon += (data_points[y][1] * numersum(test_median, data_points[y])) / denom

                    prev_median = test_median
                    test_median = (next_lat, next_lon)
                    try:
                        if vincenty(prev_median, test_median).meters < DISTANCE_THRESHOLD:
                            break
                    except:
                        if great_circle(prev_median, test_median).meters < DISTANCE_THRESHOLD:
                            break

                if x == num_iter - 1:
                    print('{0}: failed to converge. Last change between iterations was {1} meters.'.format(current_uid, great_circle(prev_median, test_median).meters))

        # Check if user points are under the limit median absolute deviation
        if check_median_absolute_deviation(data_points, test_median) <= LIMIT_MAD:
            csvwriter.writerow([current_uid, (round(test_median[0],6), round(test_median[1],6))])
        else:
            if OUTPUT_ALL_USERS:
                csvwriter.writerow([current_uid, None])


def denomsum(test_median, data_points):
    """Provides the denominator of the weiszfeld algorithm."""
    temp = 0.0
    for i in range(0, len(data_points)):
        try:
            temp += 1 / vincenty(test_median, data_points[i]).kilometers
        except ZeroDivisionError:
            continue  # filter points that equal the median out (otherwise no convergence)
        except ValueError:
            # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
            temp += 1 / great_circle(test_median, data_points[i]).kilometers
    return temp


def numersum(test_median, data_point):
    """Provides the denominator of the weiszfeld algorithm depending on whether you are adjusting the candidate x or y."""
    try:
        return 1 / vincenty(test_median, data_point).kilometers
    except ZeroDivisionError:
        return 0  # filter points that equal the median out (otherwise no convergence)
    except ValueError:
        # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
        return 1 / great_circle(test_median, data_point).kilometers


def objfunc(test_median, data_points):
    """This function calculates the sum of linear distances from the current candidate median to all points
    in the data set, as such it is the objective function that we are minimising.
    """
    temp = 0.0
    for i in range(0, len(data_points)):
        try:
            temp += vincenty(test_median, data_points[i]).kilometers
        except ValueError:
            # Vincenty doesn't always converge so fall back on great circle distance which is less accurate but always converges
            temp += great_circle(test_median, data_points[i]).kilometers
    return temp


def main(iterations=1000):
    count = 0
    with open(DATA_POINTS_FILE, 'r') as fin:
        csvreader = csv.reader(fin)
        assert next(csvreader) == ['uid','lat','lon']
        with open(OUTPUT_MEDIANS, 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(['uid','median'])
            line = next(csvreader)
            data_points = [(float(line[1]), float(line[2]))]
            current_uid = line[0]
            for line in csvreader:
                if line[0] == current_uid:
                    data_points.append((float(line[1]), float(line[2])))
                else:
                    count += 1
                    if count % 2500 == 0:
                        print("Processed {0} users.".format(count))

                    compute_user_median(data_points, iterations, csvwriter, current_uid)

                    # set user and restart array for new current user
                    current_uid = line[0]
                    data_points = [(float(line[1]), float(line[2]))]
            # compute final user median
            compute_user_median(data_points, iterations, csvwriter, current_uid)


if __name__ == "__main__":
    main()
