#!/usr/bin/env python3.9
""" Goal of this program: Help select a food truck to visit.

This works by pulling in the current list of food trucks having City of San
Francisco permits. It computes the distance to each of these as a straight
line flight: "as the crow flies" by referencing the current position as
latitude and longitude. Next a database (SQLite) is scanned to report on
all previously visited food trucks (by names) and the number of times it has
already been visited. A list of the food trucks is then produced sorted, first
by the number of times visited (ascending) and then by the distance away from
the current position. This list is output in increments of 5 trucks at a time.
The user may select one of these by entering the number given it, or move on
to the next batch of 5. Once a truck is selected, it is entered in the database
if it doesn't already exist there (with visit count 1) or the visit count is
incremented in the database.
"""

import csv
import sys
from copy import copy
import math
import sqlite3
import hashlib
import argparse
from pathlib import Path
from io import StringIO
from pprint import pprint
import __main__

import requests


EXPECTED_LABELS = ['locationid', 'Applicant', 'FacilityType', 'cnn',
  'LocationDescription', 'Address', 'blocklot', 'block', 'lot', 'permit',
  'Status', 'FoodItems', 'X', 'Y', 'Latitude', 'Longitude', 'Schedule',
  'dayshours', 'NOISent', 'Approved', 'Received', 'PriorPermit',
  'ExpirationDate', 'Location', 'Fire Prevention Districts',
  'Police Districts', 'Supervisor Districts', 'Zip Codes',
  'Neighborhoods (old)']

POSI = {'name': 1, 'type': 2, 'address': 5, 'appr': 10, 'food': 11,
        'food2': 12, 'lat':14, 'long': 15}

URL = 'https://data.sfgov.org/api/views/rqzj-sfat/rows.csv'

TYPES_OF_INTEREST = ('Truck')  # ? 'Push Cart'
TESTING = False
DEFAULT_POSITION = (37.78240, -122.40705)

# How do we convert from latitude and longitude incremental distances
# to statute miles? It is a constant conversion for latitude changes
# as every longitude line is the same distance. But for longitude changes
# the distance conversion depends on the latitude because latitude lines
# get smaller and smaller as you move closer to the poles.

# It would be ideal to compute the actual conversion for longitude changes
# based on the latitude. In the mean time, since the food trucks under
# consideration are only in San Francisco, we picked the conversion for
# some position in San Francisco and will use a contant conversion.
LAT_LONG_CONVERSION = (69.048, 54.751)
# 0.1 degree of latitude = 6.9048 miles
# 0.1 degree of longitude = 5.4751 miles

def find_crow(position1, position2):
    """ This finds the distance as the crow flies between two points, given
    as latitude, longitude tuple. The latitude and longitude are given as
    floating point values of degrees. Conversion finds the change in degrees
    of latitude between the points. Likewise the change in longitude is
    determined. Then these two values are converted into an equivalent distance
    in miles by using the LAT_LONG_CONVERSION constant (see above). Then we
    solve for the length of the hypotenuse of the right triangle formed with
    these distances as the arms of the triangle. """

    delta_lat = math.fabs(position1[0] - position2[0])
    delta_long = math.fabs(position1[1] - position2[1])
    dist_lat = delta_lat * LAT_LONG_CONVERSION[0]
    dist_long = delta_long * LAT_LONG_CONVERSION[1]
    crow_dist = math.sqrt(dist_lat*dist_lat + dist_long*dist_long)
    return crow_dist


def command_line_parsing():
    """ Parse the command line arguments, set global TESTING and return the
    current position as a tuple (either default or one given on command line """

    global TESTING
    parser = argparse.ArgumentParser(description='Food Truck Finder.')
    parser.add_argument('latlong', metavar='latlong', type=str, nargs='?',
                        help='current location as latitude,longitude '  \
                            '(no spaces)')
    parser.add_argument('--test', dest='am_testing', action='store_const',
                        const=True, default=False,
                        help='testing mode with canned data')
    args = parser.parse_args()
    TESTING = args.am_testing
    if args.latlong is None:
        return DEFAULT_POSITION

    parts = args.latlong.split(',')
    return (float(parts[0]), float(parts[1]))


def load_csv():
    """ Load either the remote CSV file or a local one used for testing, split
    it into lines, and pick off the first line as labels (and compare to the
    expected labels to detect if the CSV file may have changed format). """

    # Get the truck listing CSV file
    if not TESTING:
        # Get the remote CSV file
        csv_resp = requests.get(URL)
        csv_file = StringIO(csv_resp.text)
    else:
        # for testing, use the local file
        csv_file = open('example.csv')

    csv_reader = csv.reader(csv_file)
    return csv_reader


def sort_key(item):
    """ For sorting the results, we need a single key for the operation. Ideally
    we would have two keys, first sorting on number of visits, and then on the
    distance, both ascending. So, we can come up with a way offset the distances
    by adding a multiplier on visits. I am pretty sure distances don't exceed
    200 miles withing San Francisco, so we will multiply the visits by 200 and
    then add the distance to that. """

    key = 200 * item[1] + item[2]
    return key


def process_csv(reader, db_dict):
    """ Goes through CSV file, line-by-line, eliminates items we are not
    interested in and ensures there is a valid lat/long location. """

    results_list = list()
    header = True

    for row in reader:
        if header:
            labels = copy(row)
            if labels != EXPECTED_LABELS:
                print('ERROR: csv file format changed!')
                sys.exit(1)  # need a error lambda return here
            header = False
            continue

        # shorted or extended input line - skip them
        if len(row) != len(labels):
            print('Error: wrong # fields:')
            pprint(row)
            sys.exit(1)
        # only interested in Trucks.
        if row[POSI['type']] not in TYPES_OF_INTEREST:
            continue
        if len(row[POSI['lat']]) == 0 or len(row[POSI['long']]) == 0:
            print('empty lat/long:')
            pprint(row)
            continue
        try:
            truck_lat = float(row[POSI['lat']])
            truck_long = float(row[POSI['long']])
        except ValueError:
            print('cannot convert input to floats')
            pprint(row)
            continue
        # some entries list lat/long as 0,0. Those don't fit our algorithm, so just
        # skip them
        if truck_lat == 0.0 or truck_long == 0.0:
            continue
        if truck_lat > 180.0 or truck_long > 180.0 or  \
            truck_lat < -180.0 or truck_long < -180.0:
            continue
        # is this vendor approved? Skip if not
        if row[POSI['appr']] != 'APPROVED':
            continue

        dist = find_crow(my_position, (truck_lat, truck_long))
        hash_string = ''.join([row[POSI["name"]], row[POSI["address"]],
            row[POSI["food"]], row[POSI['lat']], row[POSI['long']]])
        hashvalue = hashlib.md5(hash_string.encode()).hexdigest()
        if hashvalue in db_dict:
            visits = db_dict[hashvalue]
        else:
            visits = 0
        entry = [hashvalue, visits, dist, row[POSI["name"]],
                 row[POSI["address"]], row[POSI["food"]]]
        results_list.append(entry)

    results_list.sort(key=sort_key)
    return results_list


def load_db():
    """ rows in db are hashvalue, visits. Read all rows and create a dictionary
    indexed on the hashvalue. """

    dict_db = dict()
    if TESTING:
        db_file_base = 'testing.db'
    else:
        db_file_base = 'database.db'
    source_path = Path(__main__.__file__)
    db_file = source_path.parent.joinpath(db_file_base)
    if db_file.exists():
        db_conne = sqlite3.connect(db_file)
        db_curso = db_conne.cursor()
        for row in db_curso.execute('SELECT hash, visits from data'):
            dict_db[row[0]] = row[1]
    else:
        db_conne = None
        db_curso = None
    return dict_db, db_conne, db_curso


def present_results_make_choice(results):
    """ Display the results, 5 at a time to allow choice of the next food
    truck to visit. """

    max_index = len(results)
    index = 0
    chose = False
    while index < max_index and not chose:
        print('\n')
        subindex = 0
        while subindex < 5 and index < max_index:
            entry = results[index]
            round_dist = round(entry[2], 1)
            print(f'{index+1}) {entry[3]}  {entry[4]}  {round_dist} mi.')
            print(entry[5])
            print()
            index += 1
            subindex += 1
        still_choosing = True
        while still_choosing:
            choice = input('enter the number you will visit, or just press '
                        'return to list more,\nor "q" to quit: ')
            if len(choice) > 0:
                try:
                    number_choice = int(choice) - 1
                    still_choosing = False
                    chose = True
                except ValueError:
                    if choice == 'q':
                        return None
                    print('invalid input, enter an integer or just press enter')
            else:
                still_choosing = False
                number_choice = -1

    if not chose:
        return None

    chosen_entry = results[number_choice]
    chosen_hash = chosen_entry[0]
    return chosen_hash


def increase_visits(save_hash, db_dict, db_conne, db_curso):
    """ Once a food truck has been chosen to visit, set or update the visits
    to that truck in the database. If there was no previous entry in the DB,
    set it to 1. Otherwise, increment the value by 1. If the database does
    not yet, exist, create it and the table """

    if len(db_dict) == 0:
        # create database
        if TESTING:
            db_file_base = 'testing.db'
        else:
            db_file_base = 'database.db'
        source_path = Path(__main__.__file__)
        db_file = source_path.parent.joinpath(db_file_base)
        db_conne = sqlite3.connect(db_file)
        db_curso = db_conne.cursor()
        db_curso.execute('CREATE TABLE data (hash text, visits integer)')

    if save_hash in db_dict:
        visits = db_dict[save_hash] + 1
        command = f"UPDATE data SET visits = {visits} WHERE "  \
                  f"hash = '{save_hash}'"
        print('comm:', command)
        db_curso.execute(command)
    else:
        visits = 1
        db_curso.execute(f"INSERT INTO data VALUES ('{save_hash}', {visits})")

    db_conne.commit()
    db_curso.close()
    db_conne.close()



my_position = command_line_parsing()
db_dict, db_conn, db_curs = load_db()
reader = load_csv()
results = process_csv(reader, db_dict)
save_hash = present_results_make_choice(results)
if save_hash is not None:
    increase_visits(save_hash, db_dict, db_conn, db_curs)
