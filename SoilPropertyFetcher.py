import requests
from urllib.parse import urlencode
import time

class SoilPropertyFetcher:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.base_url = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    def construct_url(self, properties, depth="5-15cm", value="mean"):
        query_params = {
            "lat": self.lat,
            "lon": self.lon,
            "depth": depth,
            "value": value
        }
        properties_params = [('property', prop) for prop in properties]
        query_string = urlencode(query_params) + '&' + urlencode(properties_params, doseq=True)
        return f"{self.base_url}?{query_string}"

    def fetch_properties(self, properties, retries=3, backoff_factor=2):
        results = {}
        full_url = self.construct_url(properties)

        for i in range(retries):
            response = requests.get(full_url, headers={'accept': 'application/json'})
            if response.status_code == 200:
                data = response.json()

                # Create a dictionary to map layer names to their corresponding data
                layers_map = {
                    layer['name']: layer['depths'][0]['values'].get('mean', None)
                    for layer in data['properties']['layers']
                }

                for property_name in properties:
                    mean_value = layers_map.get(property_name)
                    if mean_value is not None:
                        # the d-factor is decoded - it is included on api data
                        if property_name == 'nitrogen':
                            results[property_name] = mean_value / 100  # Convert if needed # check for it
                        else:
                            results[property_name] = mean_value / 10

                    else:
                        results[property_name] = None

                time.sleep(12)  # Prevent rate-limiting
                break

            elif response.status_code == 429:
                wait_time = (backoff_factor ** i) * 14
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

        else:
            raise Exception(f"Failed to fetch data after {retries} retries due to rate limiting.")

        return results