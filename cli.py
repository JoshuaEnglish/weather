"""weather command line utility

Gets current weather from OpenWeatherMap.org.

Based on the tutorials by Seb Vetter at
https://dbader.org/blog/python-commandline-tools-with-click
https://dbader.org/blog/mastering-click-advanced-python-command-line-apps

Turned into a full command line using entry points fromAmir Rachum's tutorial
at https://amir.rachum.com/blog/2017/07/28/python-entry-points/

OpenWeatherMaps offers a free API and requests free users do not rush the
servers and wait 10 minutes between calls for current weather. To honor this
request there is a caching mechanism that stores results and only requests
fresh data from the server if the cached response is over 10 minutes old.

If you have an OpenWeatherMap API key, the `weather config` command wil prompt
you for it.


"""

import re
import os
import sys
import logging
import json
import time
import datetime
from collections import defaultdict
from itertools import groupby

import click
import requests
import pytz

SAMPLE_API_KEY = 'b1b15e88fa797225412429c1c50c122a1'
DATA_PATH = click.get_app_dir('weather')
API = {'current': 'https://api.openweathermap.org/data/2.5/weather',
       'forecast': 'https://api.openweathermap.org/data/2.5/forecast',
       }
UTC = pytz.utc


class ApiKey(click.ParamType):
    name = 'api-key'

    def convert(self, value, param, ctx):
        found = re.match(r'[0-9a-f]{32}', value)

        if not found:
            self.fail(
                f'{value} is not a 32-character hexadecimal string',
                param,
                ctx,
            )

        return value


def build_query(ctx: click.core.Context, location: str) -> dict:
    """
    Create the query dictionary for the api using the current location or
    stored location ID
    """

    query = {
        'appid': ctx.obj['api_key'],
        'units': 'imperial',
        }

    city_data = get_city_data()

    if location.isdigit():
        query['id'] = location
    elif location in city_data:
        query['id'] = city_data[location]['id']
    else:
        query['q'] = location

    return query


def get_api_response(ctx: click.core.Context, api: str, location: str) -> dict:
    """Returns the result of a query. Will use a cached query if the cached
    query is less than 10 minutes old.

    :param ctx: current click Context object
    :param api: either 'current' or 'forecast'
    :param location: name or id code of location
    """

    if api not in API:
        raise ValueError("api must be 'current' or 'forecast'")

    datapath = os.path.join(DATA_PATH, f"{location}-{api}.json")

    if (os.path.exists(datapath)
            and (time.time() - os.stat(datapath).st_mtime) <= 600):
        with open(datapath, 'r') as fp:
            response = json.load(fp)
        logging.info("Returning cached copy of request")
        return response

    params = build_query(ctx, location)
    url = API[api]

    logging.info("Getting response from host")
    response = requests.get(url, params)

    if response.json()['cod'] not in [200, '200']:
        cod = response.json()['cod']
        message = response.json()['message']
        print(f"{cod}: {message}")
        logging.error(f"Error {cod}: {message}")
        sys.exit(1)

    logging.info("Caching response to %s", datapath)
    with open(datapath, 'w') as fp:
        json.dump(response.json(), fp)
    return response.json()


@click.group()
@click.option(
    '--api-key', '-a',
    type=ApiKey(),
    help='your API key for the OpenWeatherMap API',
)
@click.option(
    '--api-key-file', '-c',
    type=click.Path(),
    default='~/.weather.cfg',
)
@click.version_option()
@click.pass_context
def main(ctx, api_key, api_key_file):
    """
    A little weather tool that shows you the current weather in a LOCATION of
    your choice. Provide the city name and optionally a two-digit country code.
    Here are two examples:

        1. London,UK
        2. Canmore

    You need a valid API key from OpenWeatherMap for the tool to work. You can
    sign up for a free account at https://openweathermap.org/appid.
    """
    if not os.path.exists(DATA_PATH):
        logging.info("Creating default data folder")
        os.mkdir(DATA_PATH)

    if ctx.invoked_subcommand not in ["log", "open"]:
        logging.basicConfig(filename=os.path.join(DATA_PATH, 'weather.log'),
                            filemode='w',
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.INFO)

    if not os.path.isdir(DATA_PATH):
        logging.info('Creating default data file')
        os.mkdir(DATA_PATH)

    filename = os.path.expanduser(api_key_file)

    if not api_key and os.path.exists(filename):
        with open(filename) as cfg:
            api_key = cfg.read()

    ctx.obj = {
        'api_key': api_key,
        'api_key_file': filename,
    }


@main.command()
@click.pass_context
def config(ctx):
    """
    Store the API key for OpenWeatherMap.
    """
    logging.info('Setting Configuration File')
    api_key_file = ctx.obj['api_key_file']

    api_key = click.prompt(
        "Please enter your API key",
        default=ctx.obj.get('api_key', '')
    )

    with open(api_key_file, 'w') as cfg:
        cfg.write(api_key)


@main.command()
@click.pass_context
def log(ctx):
    """Print the log of the last run"""
    with open(os.path.join(DATA_PATH, 'weather.log'), 'r') as fp:
        click.echo(fp.read(), nl=False)


def get_city_data():
    """
    Returns a dictionary of previously stored city IDs.
    The list of City IDs can be download from
    http://bulk.openweathermap.org/sample/city.list.json.gz
    """
    cities_path = os.path.join(DATA_PATH, 'cities.json')
    if not os.path.exists(cities_path) or os.stat(cities_path).st_size == 0:
        logging.info("Creating empty cities file")
        with open(cities_path, 'w') as fp:
            json.dump(dict(), fp)
        return {}

    with open(cities_path, 'r') as fp:
        data = json.load(fp)
    return data


def write_city_data(city_data):
    """
    Stores the city data
    """
    cities_path = os.path.join(DATA_PATH, 'cities.json')
    with open(cities_path, 'w') as fp:
        json.dump(city_data, fp)


@main.command()
@click.argument('city')
@click.argument('cityid', type=click.INT)
@click.argument('timezone')
@click.pass_context
def setcity(ctx, city, cityid, timezone):
    """
    Save a city name with a city ID code and an optional timezone
    """
    logging.info('Setting City %s to %d', city, cityid)

    city_data = get_city_data()
    city_data[city]['id'] = cityid
    city_data[city]['timezone'] = timezone
    write_city_data(city_data)


@main.command()
@click.pass_context
def getlocations(ctx):
    """Return a list of stored locations"""
    logging.info("Getting list of stored cities")
    city_data = get_city_data()
    for key, val in city_data.items():
        print(val['id'], key, val['timezone'])


@main.command()
@click.argument('location')
@click.pass_context
def current(ctx, location):
    """
    Show the current weather for a location using OpenWeatherMap data.
    """
    logging.info("Getting current weather for %s", location)
    response = get_api_response(ctx, 'current', location)

    weather = response['weather'][0]['description']
    print(f"The weather in {location} right now: {weather}.")


@main.command()
@click.argument('location')
@click.pass_context
def temp(ctx, location):
    """
    Show the current temperature and low and high
    """
    logging.info("Getting temperature for %s", location)
    response = get_api_response(ctx, 'current', location)
    temp = response['main']['temp']
    low = response['main']['temp_min']
    high = response['main']['temp_max']
    print(f"Current Temperature is {temp} with a low of {low} "
          f"and a high of {high}")


@main.command()
@click.argument('location')
@click.pass_context
def dump(ctx, location):
    """
    Show the json response for current weather information
    """
    logging.info("Getting JSON dump for %s", location)
    response = get_api_response(ctx, 'current', location)
    print(response)


def date_bit(text):
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S").date()


@main.command()
@click.argument('location')
@click.pass_context
def forecast(ctx, location):
    """
    List the lows and highs for the next few days
    """
    logging.info("Getting 5-day highs forcast")
    response = get_api_response(ctx, 'forecast', location)
    data = defaultdict(list)

    for thing in response['list']:
        data[date_bit(thing['dt_txt'])].append(
                (float(thing['main']['temp_min']),
                 float(thing['main']['temp_max']),
                 thing['weather'][0]['description']))

    for day in sorted(data):
        print(day,
              "{:5.2f}".format(min([item[0] for item in data[day]])),
              "{:5.2f}".format(max([item[1] for item in data[day]])),
              ', '.join([k for k, g
                         in groupby(item[2] for item in data[day])]))


@main.command()
@click.argument('location')
@click.pass_context
def howmuchrain(ctx, location):
    """
    Total the amount of rain for the next five days.
    """
    logging.info("Getting 5-day rain totals")
    response = get_api_response(ctx, 'forecast', location)
    data = defaultdict(float)

    for thing in response['list']:
        if 'rain' in thing:
            data[date_bit(thing['dt_txt'])] += thing['rain'].get('3h', 0.0)

    for day in sorted(data):
        print(f"{day:%a %m/%d} {data[day]:5.2f}mm",
              f"({data[day]*0.03937:0.02} inches)")
    total = sum(data[day] for day in data)
    print(f"Total: {total:.2f}mm ({total*0.03937:.3f} inches)")


@main.command()
@click.argument('location')
@click.pass_context
def daylight(ctx, location):
    """
    Today's sunrise and sunset
    """
    logging.info("Getting Sunrise and Sunset data")
    response = get_api_response(ctx, 'current', location)
    city_data = get_city_data()[location]
    sunrise = datetime.datetime.utcfromtimestamp(response['sys']['sunrise'])
    sunset = datetime.datetime.utcfromtimestamp(response['sys']['sunset'])
    here = pytz.timezone(city_data['timezone'])
    sunrise = UTC.localize(sunrise).astimezone(here)
    sunset = UTC.localize(sunset).astimezone(here)
    print(f"Daylight Hours: {sunrise:%I:%M %p} - {sunset:%I:%M %p}")


@main.command()
@click.pass_context
def showdata(ctx):
    """Opens the data folder"""
    os.startfile(DATA_PATH)
