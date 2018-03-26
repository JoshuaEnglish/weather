# weather
Command Line Weather Tool

Gets current weather from OpenWeatherMap.org.

Based on the tutorials by Seb Vetter at
https://dbader.org/blog/python-commandline-tools-with-click
https://dbader.org/blog/mastering-click-advanced-python-command-line-apps

Turned into a full command line using entry points fromAmir Rachum's tutorial at
https://amir.rachum.com/blog/2017/07/28/python-entry-points/

OpenWeatherMaps offers a free API and requests free users do not rush the
servers and wait 10 minutes between calls for current weather. To honor this
request there is a caching mechanism that stores results and only requests
fresh data from the server if the cached response is over 10 minutes old.

