"""weather command line tool

Gets current weather from OpenWeatherMap.org.

Based on the tutorials by Seb Vetter at
https://dbader.org/blog/python-commandline-tools-with-click
https://dbader.org/blog/mastering-click-advanced-python-command-line-apps

Turned into a full command line using entry points fromAmir Rachum's tutorial at
https://amir.rachum.com/blog/2017/07/28/python-entry-points/

OpenWeatherMaps offers a free API and requests free users do not rush the
servers and wait 10 minutes between calls for current weather. The third version
of this code will then store the results of a previous call and retrieve it
if it is within a given time frame. I'm going to use 10 minutes here.

Before I implement that I want to implement logging

And then I want to implement using City IDs instead of names. I may not be
getting results for my Portland.

Once the simple logging mechanism is built, the next step is to decide how
to data will be stored.

"""
import re
import os
import logging
import json
import time

import click
import requests

SAMPLE_API_KEY = 'b1b15e88fa797225412429c1c50c122a1'
DATA_PATH = os.path.abspath('.\data')
API = {'current': 'https://api.openweathermap.org/data/2.5/weather',
       'forecast': 'https://api.openweathermap.org/data/2.5/forecast',
       }


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

    query = {
        'appid': ctx.obj['api_key'],
        'units': 'imperial',
        }

    city_data = get_city_data()

    if location.isdigit():
        query['id'] = location
    elif location in city_data:
        query['id'] = city_data[location]
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
    logging.basicConfig(filename='weather.log',
                        filemode='w',
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.INFO)

    if not os.path.isdir(DATA_PATH):
        logging.info('Creating default data file')
        os.mkdir(DATA_PATH)

    logging.info('Starting Weather CLI')
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


def get_city_data():
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
    cities_path = os.path.join(DATA_PATH, 'cities.json')
    with open(cities_path, 'w') as fp:
        json.dump(city_data, fp)


@main.command()
@click.argument('city')
@click.argument('cityid', type=click.INT)
@click.pass_context
def setcity(ctx, city, cityid):
    """
    Save a city name with a city ID code
    """
    logging.info('Setting City %s to %d', city, cityid)

    city_data = get_city_data()
    city_data[city] = cityid
    write_city_data(city_data)


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
