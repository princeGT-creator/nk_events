import requests

token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoyMzUsImFjY291bnQiOiJuZXRpY2siLCJjbGllbnRfdHlwZSI6Im9wZW5hcGkiLCJjbGllbnQubmFtZSI6Im9wZW5hcGkiLCJleHAiOjIwNTU5MjI2ODAsImlzcyI6IntcIm5hbWVcIjpcImJhY2tlbmRcIixcInZlcnNpb25cIjpcIjQuNzE4LjAuMVwifSIsImlhdCI6MTc0MDM4OTg4MH0.ZugfDGQU7XeuxBA49Urc1B8kaEvMn_Y23Hk8OiwqhRQ'

def get_rentman_contacts(api_key):
    """
    Fetches the list of contacts from Rentman API.

    :param api_key: Authorization token for API access
    :return: API response JSON
    """

    url = "https://api.rentman.net/contacts"

    headers = {
        'Authorization': api_key
    }

    response = requests.get(url, headers=headers)

    try:
        data = response.json()  # Ensure response is parsed as JSON
        if isinstance(data, dict) and 'data' in data:
            return data['data']
        else:
            print("Unexpected Fatture API response format:", data)
            return []
    except requests.exceptions.JSONDecodeError:
        print("Failed to decode JSON from Fatture API response:", response.text)
        return []


def get_rentman_customer_name(id):
    """
    Fetches the list of contacts from Rentman API.

    :param api_key: Authorization token for API access
    :return: API response JSON
    """

    url = f"https://api.rentman.net{id}"

    headers = {
        'Authorization': token
    }

    response = requests.get(url, headers=headers)

    try:
        data = response.json()  # Ensure response is parsed as JSON
        if isinstance(data, dict) and 'data' in data:
            return data['data']
        else:
            print("Unexpected Rentman API response format:", data)
            return None  # Return None if the response format is unexpected
    except requests.exceptions.JSONDecodeError:
        print("Failed to decode JSON from Rentman API response:", response.text)
        return None  # Return None if JSON decoding fails


def get_customers():
    url = "https://api.rentman.net/contacts"
    headers = {'Authorization': token}
    customers = []
    offset = 0
    limit = 300  # Adjust if the API allows a larger limit

    while True:
        params = {"offset": offset, "limit": limit}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            break
        
        data = response.json()
        contacts = data.get("data", [])
        
        for item in contacts:
            print('item: ', item)
            customers.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "vat_number": item.get("VAT_code")
            })
        
        if len(contacts) < limit:
            break  # Stop when the last batch has fewer than `limit` contacts
        
        offset += limit  
    
    return customers


# Example usage:
# api_key = "your_api_key_here"
# contacts_data = get_rentman_contacts(api_key)
# print(contacts_data)
