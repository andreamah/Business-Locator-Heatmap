import geopandas as gpd
import folium
from folium.plugins import HeatMap
import pandas as pd
import json
import requests
import csv
import sys
try:
    # For Python 3.0 and later
    from urllib.error import HTTPError
except ImportError:
    # Fall back to Python 2's urllib2 and urllib
    from urllib2 import HTTPError

API_KEY = 'iloYNi4xU0w6dN2Bi6k5H26zD5ftng1cPMYVqbc3sYO-pMme5dpIP0DvT7Bmk_65N0juMPblI7vFCDISx9gicPGD2aaJOYatgIa4Xiwk2e3m6wdxKI6ShWx_Qx0bXHYx'

# function borrowed from https://github.com/Yelp/yelp-fusion/blob/master/fusion/python/sample.py
def request(host, path, api_key, url_params=None):
    """Given your API_KEY, send a GET request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        API_KEY (str): Your API Key.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    url = host + path;
    headers = {
        'Authorization': 'Bearer %s' % api_key,
    }

    # print(u'Querying {0} ...'.format(url))

    response = requests.request('GET', url, headers=headers, params=url_params)

    return response.json()

def main():
    #initial data collection
    location = input('Choose a location to find some boba in!\nYou may enter various location, separated by "or" (ie: Vancouver or Richmond, BC or Burnaby, )\n>')

    ratings_weighted = 3
    while ratings_weighted == 3:
        ratings_weighted_resp = input('Would you like higher-rated restaurants to show more intensely on the map? (yes/no)\n>')
        if ratings_weighted_resp == 'yes':
            ratings_weighted = 1
        elif ratings_weighted_resp == 'no':
            ratings_weighted = 0
        else:
            print('Your response is invalid. Try again.\n')

    #send the API request
    try:
        response_json = request('https://api.yelp.com/v3/businesses/search?', 'location='+location+'&categories=bubbletea&limit=50', API_KEY)
    except HTTPError as error:
        sys.exit(
            'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                error.code,
                error.url,
                error.read(),
            )
        )

    #response has no results if it's an invalid location
    response_businesses = response_json['businesses'];
    if len(response_businesses) == 0:
        sys.exit('\nLocation does not have any boba shops or location does not exist :(')

    #open a csv file to write to
    f = csv.writer(open("featured_location_results.csv", "w", encoding="ISO-8859-1"), lineterminator='\n')

    # write csv header
    headers = ['Name', 'lat', 'lon', 'Amount', 'City']
    f.writerow(headers)

    #form business data in 2D array while also writing to csv file
    list_of_businesses=[]
    for entry in response_businesses:
        if ratings_weighted:
            amount_entry = entry["rating"]
        else:
            amount_entry = 1.5
        row = [entry["name"],
                    entry["coordinates"]["latitude"],
                    entry["coordinates"]["longitude"],
                    amount_entry,
                    entry['location']['city']]
        f.writerow(row)
        list_of_businesses.append(row);

    #turn table of data to pandas dataframe
    for_map = pd.DataFrame(list_of_businesses)
    for_map.columns = headers

    print(for_map)

    #initialize data for forming folium map and form map
    #referenced from https://alcidanalytics.com/p/geographic-heatmap-in-python
    response_center = response_json['region']['center'];
    hmap = folium.Map(location=[response_center['latitude'], response_center['longitude']], zoom_start=11, )

    hm_wide = HeatMap( list(zip(for_map.lat.values, for_map.lon.values, for_map.Amount.values)),
                       min_opacity=0.2,
                       max_val=5,
                       radius=17, blur=15,
                       max_zoom=1,
                     )

    hmap.add_child(hm_wide)
    hmap.save('heatmap.html')

    print('\nDone! Check the folder for heatmap.html.')

if __name__ == '__main__':
    main()
