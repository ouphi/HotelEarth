#  Imports
import pprint
import re
import datetime
import lxml.html as LH
import requests

from io import BytesIO
from lxml.cssselect import CSSSelector

from pyspark import SparkContext, SparkConf
from pyspark.sql import SQLContext
conf = SparkConf().setAppName("HotelEarth")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)



#  Constants
COUNTRIES_PER_CHUNK = 1
BOOKING_URL_PREFIX = 'https://www.booking.com'
BOOKING_COUNTRIES_URL = '/destination.en-gb.html'
INFLUXDB_DB_NAME = 'hotel_earth'
INFLUXDB_TABLE_NAME = 'booking_parser_activity'
INFLUXDB_WRITE_URL = "http://localhost:8086/write?db="+INFLUXDB_DB_NAME
INFLUXDB_QUERY_URL = "http://localhost:8086/query?db="+INFLUXDB_DB_NAME
CASSANDRA_KEYSPACE_NAME = "hotel_earth"
CASSANDRA_TABLE_NAME = "booking"



#  Functions
def count_in_a_partition(iterator):
  yield sum(1 for _ in iterator)
  
  
def repartitionate(rdd, tag):
	print("\tNow parsing "+str(rdd.count())+" " +str(tag)+ " ...");
	rdd_partitions = rdd.getNumPartitions()
	rdd = rdd.partitionBy(rdd_partitions)
	print("\tRepartion: " + str(rdd_partitions) + " => " + str(rdd.mapPartitions(count_in_a_partition).collect()))
	return rdd
  
  
def log_influxdb(tag):
	'''
	Logs a tag to a local influx DB database'
	tag: The tag string to log
	'''
	requests.post(INFLUXDB_WRITE_URL, INFLUXDB_TABLE_NAME+" "+str(tag)+"=1")
	
def clean_influxdb():
	'''
	Cleans the influxdb database
	'''
	requests.post(INFLUXDB_QUERY_URL, params={"q":"DELETE FROM "+INFLUXDB_TABLE_NAME+";"}).text



def css_select(dom, selector):
    '''
    css selector
    '''
    from lxml.cssselect import CSSSelector as CS
    sel = CS(selector)
    return sel(dom)


def map_cities(country_url):
    '''
    Parse Booking web page with every cities corresponding to a country
    and retreive cities and their URL
    country_url : URL corresponding to a country, containing every cities
    of the country
    Return cities : list of URL corresponding to a city
    '''
    content = requests.get(country_url).text
    log_influxdb("parsed_countries")
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
    content = requests.get(city_url).text
    log_influxdb("parsed_cities")
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
    content = requests.get(url).text
    log_influxdb("parsed_hotels")
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




#  App
#  Retrieve Countries
content = requests.get(BOOKING_URL_PREFIX+BOOKING_COUNTRIES_URL).text
log_influxdb("parsed_world")
dom = LH.fromstring(content)
sel = CSSSelector('.flatList a')
all_countries = sel(dom)
all_countries = [(re.sub(r'\W+', '_', result.text), BOOKING_URL_PREFIX+result.get('href')) for result in all_countries]
len_countries = len(all_countries)
print("There are "+str(len_countries)+ " countries.")
print("They will be processed by chunks of " + str(COUNTRIES_PER_CHUNK) + ".")



# Loop through them, we don't use spark but a regular for to have time checkpoints and not be forced to compute all the data in one time
for i in range(0,1+(len_countries/COUNTRIES_PER_CHUNK)):
	clean_influxdb()

	countries = all_countries[i*COUNTRIES_PER_CHUNK: (i+1)*COUNTRIES_PER_CHUNK]
	print("Processing country chunk #"+str(i)+" => from #"+str(i*COUNTRIES_PER_CHUNK)+ " to #" +str((i+1)*COUNTRIES_PER_CHUNK-1)+ " ...")
	countries = sc.parallelize(countries)
	countries = repartitionate(countries, "countries")
	
	
	# Retrieves Cities
	cities = countries.flatMapValues(map_cities)
	cities = cities.map(lambda c: ((c[0], c[1][0]), c[1][1]))
	cities = repartitionate(cities, "cities")
	
	
	# Retrieve Hotels
	hotels = cities.flatMapValues(map_hotels)
	hotels = hotels.map(lambda c: ((c[0][0], c[0][1], c[1][0]), c[1][1]))
	hotels = repartitionate(hotels, "hotels")
	
	
	# Retrieve Informations
	hotels = hotels.mapValues(parse_booking_hotel_page)
	hotels = hotels.map(lambda c: (c[0][0], c[0][1], c[0][2], c[1][0], c[1][1], c[1][2], c[1][3], c[1][4], c[1][5]))
	
	# Saving Informations
	df = hotels.toDF(['country', 'city', 'name', 'url', 'latitude', 'longitude', 'rate', 'address', 'pictures'])
	df.write\
	    .format("org.apache.spark.sql.cassandra")\
	    .mode('append')\
	    .options(keyspace=CASSANDRA_KEYSPACE_NAME, table=CASSANDRA_TABLE_NAME)\
	    .save()
	print("\tChunk successfully saved !!!\n")