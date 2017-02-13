#  Imports
import re
import pycurl
import lxml.html as LH

from io import BytesIO
from lxml.cssselect import CSSSelector


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

