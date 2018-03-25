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

import click
import requests

SAMPLE_API_KEY = 'b1b15e88fa797225412429c1c50c122a1'
CURRENT_WEATHER_API = 'https://api.openweathermap.org/data/2.5/weather'
FORECAST_API = 'https://api.openweathermap.org/data/2.5/forecast'
DATA_PATH = os.path.abspath('.\data')


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


def current_weather(location, api_key=SAMPLE_API_KEY):

    query_params = {
        'q': location,
        'appid': api_key,
    }

    response = requests.get(CURRENT_WEATHER_API, params=query_params)

    return response.json()['weather'][0]['description']


def current_temp(location, api_key=SAMPLE_API_KEY):

    query_params = {
        'q': location,
        'appid': api_key,
        'units': 'imperial',
        }

    response = requests.get(CURRENT_WEATHER_API, params=query_params)

    data = response.json()['main']

    return data['temp'], data['temp_min'], data['temp_max']


@click.group()
@click.option(
    '--api-key', '-a',
    type=ApiKey(),
    help='your API key for the OpenWeatherMap API',
)
@click.option(
    '--config-file', '-c',
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
    Store configuration values in a file, e.g. the API key for OpenWeatherMap.
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
@click.argument('location')
@click.pass_context
def current(ctx, location):
    """
    Show the current weather for a location using OpenWeatherMap data.
    """
    logging.info("Getting current weather for %s", location)
    api_key = ctx.obj['api_key']

    weather = current_weather(location, api_key)
    print(f"The weather in {location} right now: {weather}.")


@main.command()
@click.argument('location')
@click.pass_context
def temp(ctx, location):
    """
    Show the current temperature and low and high
    """
    logging.info("Getting temperature for %s", location)
    api_key = ctx.obj['api_key']
    temp, low, high = current_temp(location, api_key)
    print(f"Current Temperature is {temp} with a low of {low} "
          f"and a high of {high}")


@main.command()
@click.argument('location')
@click.pass_context
def dump(ctx, location):
    logging.info("Getting JSON dump for %s", location)
    query_params = {
        'q': location,
        'appid': ctx.obj['api_key'],
        'units': 'imperial'}
    response = requests.get(CURRENT_WEATHER_API, params=query_params)
    print(response.json())
    logging.info("Dumping JSON data to dump.json")
    with open(os.path.join(DATA_PATH,'dump.json'), 'w') as fp:
        json.dump(response.json(), fp)


if __name__ == "__main__":
    main()
