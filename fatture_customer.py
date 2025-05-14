import requests

def get_clients_list(api_key):
    """
    Fetches the complete list of clients from Fatture in Cloud API, handling pagination and JSON errors.

    :param api_key: Authorization token for API access
    :return: List of all clients
    """

    base_url = "https://secure.fattureincloud.it/backend_apiV2/entities/clients"
    page = 1
    all_clients = []

    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'it',
        'authorization': api_key,
        'content-type': 'application/json; charset=utf-8',
        'priority': 'u=1, i',
        'referer': 'https://secure.fattureincloud.it/clients',
        'user-agent': 'Mozilla/5.0'
    }

    while True:
        url = f"{base_url}?fieldset=fic_list&page={page}&sort=name"
        response = requests.get(url, headers=headers)

        try:
            data = response.json()  # Ensure response is parsed as JSON
            if isinstance(data, dict) and 'data' in data:
                clients = data['data']
                if not clients:
                    break  # Stop if no more data is returned
                all_clients.extend(clients)
                page += 1  # Move to the next page
            else:
                print("Unexpected Fatture API response format:", data)
                return []  # Return empty list if response format is invalid
        except requests.exceptions.JSONDecodeError:
            print("Failed to decode JSON from Fatture API response:", response.text)
            return []  # Return empty list if JSON decoding fails

    return all_clients

# Example usage:
# api_key = "your_api_key_here"
# all_clients = get_clients_list(api_key)
# print(f"Total clients fetched: {len(all_clients)}")
