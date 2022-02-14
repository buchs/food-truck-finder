# food-truck-finder

## Customer Needs

The customers for this application reported the following information on their
needs:

> Our team loves to eat. They are also a team that loves variety, so they also
like to discover new places to eat. In fact, we have a particular affection for
food trucks. One of the great things about Food Trucks in San Francisco is that
the city releases a list of them as open data.

## Design

This application is designed to be a command line tool to help the team
select the next food truck they will visit. The user is presented with a
menu of food trucks and can choose one to visit. The menu would be awkward if
presented with over 200 food trucks available to choose from. So, the menu is
presented with 5 choices at a time. One of those 5 can be selected by entering
its number (the total list is numbered sequentially starting at 1).
Alternatively, the user can opt to go on to the next 5 items by entering a
empty line with return/enter. The process continues until the user selects
a truck to visit. One other option is to enter "q" to quit the application
without making a selection.

Since the customer needs indicate the team likes to discover new places to eat,
the list of choices are ordered. First come food trucks that haven't been
visited. After that comes those which have been visited one time. And, then
two times, etc.

There is also a secondary sorting of the listing, which is the distance from
the user's current location. Now, there is a default location which is that
of the Team's office in San Francisco. But, alternate locations can be given
by providing the latitude and longitude on the command line. These two numbers
are given as decimals, and they are separated by a comma, and only a comma.
For example: 37.78240,-122.40705.

Each time the application is run, it retrieves the latest food truck
information from the city of San Francisco via an Internet http request.

A local file-based Sqlite database is used to keep the record of food trucks
visited. This means the application really only functions completely at a given
installation on a computer, unless the database file is copied to another
location on another machine. This database is located where the food_trucker.py
program is located.

## Setup and Execution Environment

This application uses Python and was developed under Python version 3.9.
However, it should run properly in any version of Python at 3.6 or higher. The
program, food_trucker.py, begins with a "she-bang" line that would allow direct
execution (i.e. without giving python on the command line) if the python3.9
command can be found on the user's path. However, this line can easily be
changed to python3 or another specific version, like python3.7. However, one
can also give python on the command line like: python3.6 food_trucker.py.

If Python 3.6 or above is not available on your machine, you can install it in
numerous ways, including downloading the standard version from the Python
Software Foundation (PSF) at https://www.python.org/downloads/. 

Additionally, one non-standard Python module must be installed. It is the very
common module "requests". There are many different ways to install this,
which depend upon how python was installed on your machine. If you install the
PSF Python, then the pip utility is available, as pip3. To install requests,
use the commad `pip3 install requests`.

As is usually the case, installing this application means putting it in a
specific location in the filesystem. To execute it, the program must be
unambiguously addressed by either giving the full file system path to reach
the location of food_trucker.py or to have the directory containing the
food_trucker.py file on the system **path**. Consult your operating system
documentation to understand these options.

## Testing

This application was fully tested as part of development. However, time ran
short to fully automate this testing. 

The following capabilities were provided to support functional testing: (1) use
of a static version of the input food truck data, rather than downloading live
data that could change regularly and (2) a special named SQLite database file
that can isolate testing from routine execution. The static version of the
input data comes from the file example.csv found in this repository. One must
have the current directory set to the same as the one containing this file.
The database file is switched from the default **database.db** to
**testing.db**. Both of these capabilities are triggered by using the command
line argument **--test**.

These capabilities would support the most effective functional testing, which
would involve a series of executions of food_trucker.py --test, providing fixed
input to select certain food trucks for each run. Then the final state of the
database can be dumped and compared to the expected value. Further, the
output of the program execution could also be captured and compared to 
expected values. 

## Future Development

Ideally this application would be deployed such that anyone on the team could
execute it from any location. I believe the best way to implement this would
involve an AWS Lambda function (if on AWS, Cloud Functions on the other two)
for the code execution. It would also include use of AWS DynamoDB for the
database. The Lambda function could provide a web based interface, serving up
a static HTML page when a GET request of the default **/** URL is used but
taking the optional arguments of a user location (latitude/longitude) in a
POST request to the same **/** URL. Then the response would be HTML listing
all the food trucks, sorted as currently provided, which the ability to
indicate which one will be visited next.