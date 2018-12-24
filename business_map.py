# import geopandas as gpd
import folium
from folium.plugins import HeatMap
from folium import FeatureGroup, LayerControl, Map, Marker
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

API_KEY = '' #API KEY

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

def create_heatmap(location_table, map_title, show_map, print_table = False):
    """Given map data and an option for printing data, create a heatmap and return its FeatureGroup and and DataFrame
    Args:
        location_table (array): A table containing location (latitude and longitude) data.
        map_title (str): The name of the heatmap on the LayerControl.
        show_map (bool): Whether the map should be visible by default.
        print_table (bool): Whether this table should be printed to the console and CSV file.
    Returns:
        hm: The FeatureGroup containing the resultant heatmap.
        for_map: The DataFrame containing the location_table data
    """
    #turn table of data to pandas dataframe
    for_map = pd.DataFrame(location_table)
    for_map.columns = ['Name', 'lat', 'lon', 'Amount','Address','City']

    #drop entries with no location values
    for_map = for_map.dropna(subset=['lon','lat'])

    #try to print table on console
    if print_table:
        try:
            print(for_map)
        except UnicodeEncodeError:
            print('\nCannot print table here due to issue in character decoding. Check featured_location_results.csv')

        for_map.to_csv("featured_location_results.csv", encoding='utf8')

    #initialize data for forming folium map and form map
    #referenced from https://alcidanalytics.com/p/geographic-heatmap-in-python
    hm = FeatureGroup(name=map_title, show=show_map)
    hm_formed = HeatMap(list(zip(for_map.lat.values, for_map.lon.values, for_map.Amount.values)),
                       min_opacity=0.2,
                       max_val=5,
                       radius=17, blur=15,
                       max_zoom=1,
                     )
    hm.add_child(hm_formed)
    return hm, for_map

def create_markermap(for_map,map_title):
    """Given the pandas dataframe, it makes a FeatureGroup containing all of the location markers.
    Args:
        for_map (DataFrame): The dataframe containing the location (latitude and longitude) and name values.
        map_title (str): The title of the group in the LayerControl.
    Returns:
        FeatureGroup: The FeatureGroup that contains all of the location markers
    """
    locmap = FeatureGroup(name=map_title, show=False)

    #add markers for each location to the FeatureGroup
    for i in range(0,len(for_map)):
        folium.Marker( [for_map.iloc[i]['lat'], for_map.iloc[i]['lon']], tooltip=for_map.iloc[i]['Name']).add_to(locmap)

    return locmap

def main():
    #initial data collection
    location = input('Choose a location to search in and around!\nYou may enter various locations, separated by "or" (ie: Vancouver or Richmond, BC or Burnaby)\n>')

    #find category to search with
    search_category = ''

    while search_category == '':
        autocomplete_text = input('\nSearch for a category that you would like to locate on the map.\n>')

        #request yelp to autocomplete
        try:
            response_json_autocomplete = request('https://api.yelp.com/v3/autocomplete?', 'text={0}'.format(autocomplete_text), API_KEY)
        except HTTPError as error:
            sys.exit(
                'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                    error.code,
                    error.url,
                    error.read(),
                )
            )

        #if no results, prompt user to search again
        if len(response_json_autocomplete['categories']) == 0:
            while 1:
                no_results_resp = input('\nNo results. Would you like to search again? ([yes]/no)\n>')
                if no_results_resp == 'yes' or no_results_resp == '':
                    break
                elif no_results_resp == 'no':
                    sys.exit('Exited program.')
                else:
                    print('Your response is invalid. Try again.\n')

        #if results appear, ask user to choose and store alias value from it
        else:
            print('\nThe result(s) from the search is/are:')

            search_results = []
            j = 0
            #print results and add them to search_results array to keep track of aliases
            for entry in response_json_autocomplete['categories']:
                search_results.append(entry['alias'])
                print('({0}) {1}\t'.format(j,entry['title']))
                j += 1

            while 1:
                search_int = input('\nPlease enter the corresponding number for your desired category or type "no" to search again\n>')

                if search_int == 'no':
                    break

                try:
                    if int(search_int) >= len(search_results) or int(search_int) < 0:
                        print('Number out of range. Please try again.\n')
                        continue
                except ValueError:
                    print('You did not input a number value. Please try again.\n')

                search_category = search_results[int(search_int)]
                break


    list_of_businesses=[]
    list_of_businesses_weighted=[]

    #make multiple calls to get all results or max results, changing offset by the return limit
    current_offset = 0
    max_results = 2
    while current_offset <= max_results and current_offset<=950:
        #send the API request
        try:
            response_json = request('https://api.yelp.com/v3/businesses/search?', 'location={0}&categories={1}&limit=50&offset={2}&locale=en_CA'.format(location,search_category,current_offset), API_KEY)
        except HTTPError as error:
            sys.exit(
                'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                    error.code,
                    error.url,
                    error.read(),
                )
            )

        #response has no results if it's an invalid location
        try:
            response_businesses = response_json['businesses'];
        except KeyError:
            print('Location not found. Try again.\n')
            main()

        if len(response_businesses) == 0:
            if max_results == 2:
                sys.exit('\nError: one or more of the following has occurred:\n'+
                ' - Location does not have any results available for that category\n'+
                ' - This category is not available for this country')
            else:
                break

        current_offset += 50
        max_results = response_json['total']

        #form business data in 2D array
        for entry in response_businesses:

            row = [entry["name"],
                        entry["coordinates"]["latitude"],
                        entry["coordinates"]["longitude"],
                        1,
                        entry['location']['address1'],
                        entry['location']['city']]

            row_weighted = [entry["name"],
                        entry["coordinates"]["latitude"],
                        entry["coordinates"]["longitude"],
                        entry["rating"],
                        entry['location']['address1'],
                        entry['location']['city']]

            list_of_businesses.append(row);
            list_of_businesses_weighted.append(row_weighted);

    #slightly referenced from https://alcidanalytics.com/p/geographic-heatmap-in-python
    #form main map
    response_center = response_json['region']['center'];
    map = folium.Map(location=[response_center['latitude'], response_center['longitude']], zoom_start=11, )

    #initialize pandas dataframes and form folium maps (heatmap and location marker maps)
    hm_eqw, for_map = create_heatmap(list_of_businesses,'Heat Map (Equal Weight)', True)
    hm_w, for_map = create_heatmap(list_of_businesses_weighted,'Heat Map (Weighted by Rating)', False, True)
    locmap = create_markermap(for_map,'Location Labels')

    #add featuregroups of different maps to main map
    hm_eqw.add_to(map)
    hm_w.add_to(map)
    locmap.add_to(map)

    #add layer controls
    folium.LayerControl(collapsed=False).add_to(map)

    map.save('heatmap.html')

    print('\nDone! Check the folder for heatmap.html.')

if __name__ == '__main__':
    main()
