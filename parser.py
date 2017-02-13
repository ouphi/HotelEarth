#  Imports
import pprint
import re
import pycurl
import datetime
import lxml.html as LH

from io import BytesIO
from lxml.cssselect import CSSSelector

from pyspark import SparkContext, SparkConf
from pyspark.sql import SQLContext
conf = SparkConf().setAppName("HotelEarth")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)


def css_select(dom, selector):
    '''
    css selector
    '''
    from lxml.cssselect import CSSSelector as CS
    sel = CS(selector)
    return sel(dom)


def simple_curl(url):
    '''
    Does a curl query using the url as parameter and follow every HTTP queries
    url : An url
    return : Result of curl query
    '''
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(pycurl.FOLLOWLOCATION, True)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    body = buffer.getvalue()
    return body.decode(BOOKING_CHARSET)


def map_cities(country_url):
    '''
    Parse Booking web page with every cities corresponding to a country
    and retreive cities and their URL
    country_url : URL corresponding to a country, containing every cities
    of the country
    Return cities : list of URL corresponding to a city
    '''
    content = simple_curl(country_url)
    dom = LH.fromstring(content)
    sel = CSSSelector('[name=cities] + h3 + .general a')
    cities = sel(dom)
    cities = [(result.text, BOOKING_URL_PREFIX+result.get('href')) for result in cities]
    return cities


def map_hotels(city_url):
    '''
    Parse Booking web page with list of hotels corresponding to a city and retreive hotels and URL
    containing informations about these hotels
    city_url : URL corresponding to a city, containing every hotels of the city
    Return cities : list of url corresponding to an hotel
    '''
    content = simple_curl(city_url)
    dom = LH.fromstring(content)
    sel = CSSSelector('[name=hotels] + h3 + .general a')
    hotels = sel(dom)
    hotels = [(result.text, BOOKING_URL_PREFIX+result.get('href')) for result in hotels]
    return hotels


def parse_booking_hotel_page(url):
    '''
    Receive an URL corresponding to a hotel webpage, parse informations about the hotel and
    return a dictionary with these informations
    '''
    #  get html
    content = simple_curl(url)
    dom = LH.fromstring(content)
    #  get latitude
    latitude = re.findall('booking.env.b_map_center_latitude = ([-\.\d]+)', content)
    latitude = latitude[0] if len(latitude) > 0 else -1
    #  get longitude
    longitude = re.findall('booking.env.b_map_center_longitude = ([-\.\d]+)', content)
    longitude = longitude[0] if len(longitude) > 0 else -1
    #  get the rate
    tmp_rate = css_select(dom, 'span.average, span.js--hp-scorecard-scoreval, [itemprop="ratingValue"]')
    rate = tmp_rate[0].text if len(tmp_rate) > 1 else -1
    #  get the address
    address = css_select(dom, 'span.hp_address_subtitle')
    #  get images link
    pictures = css_select(dom, 'div#photos_distinct a')
    pictures = [result.get('href') for result in pictures]
    return (url, float(latitude), float(longitude), float(rate), address[0].text, pictures)


#  Constants
BOOKING_URL_PREFIX = 'https://www.booking.com'
BOOKING_COUNTRIES_URL = '/destination.en-gb.html'
BOOKING_CHARSET = 'UTF-8'
CITY_FILTER = 'Boston'

#  Retrieve Countries
content = simple_curl(BOOKING_URL_PREFIX+BOOKING_COUNTRIES_URL)
dom = LH.fromstring(content)
sel = CSSSelector('.flatList a')
countries = sel(dom)
countries = [(result.text, BOOKING_URL_PREFIX+result.get('href')) for result in countries]
countries = sc.parallelize(countries)

# Retrives Cities
cities = countries.flatMapValues(map_cities)
cities = cities.map(lambda c: ((c[0], c[1][0]), c[1][1]))
cities = cities.filter(lambda c: c[0][1] == 'Vaucresson')

# Retrieve Hotels
hotels = cities.flatMapValues(map_hotels)
hotels = hotels.map(lambda c: ((c[0][0], c[0][1], c[1][0]), c[1][1]))
hotels = hotels.mapValues(parse_booking_hotel_page)
hotels = hotels.map(lambda c: (c[0][0], c[0][1], c[0][2], c[1][0], c[1][1], c[1][2], c[1][3], c[1][4], c[1][5]))

df = hotels.toDF(['country', 'city', 'name', 'url', 'latitude', 'longitude', 'rate', 'address', 'pictures'])
#pprint.pprint(df.collect())
#exit()
df.write\
    .format("org.apache.spark.sql.cassandra")\
    .mode('append')\
    .options(keyspace="hotel_earth", table="booking_parser")\
    .save()
