import requests
import json

token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoyMzUsImFjY291bnQiOiJuZXRpY2siLCJjbGllbnRfdHlwZSI6Im9wZW5hcGkiLCJjbGllbnQubmFtZSI6Im9wZW5hcGkiLCJleHAiOjIwNTU5MjI2ODAsImlzcyI6IntcIm5hbWVcIjpcImJhY2tlbmRcIixcInZlcnNpb25cIjpcIjQuNzE4LjAuMVwifSIsImlhdCI6MTc0MDM4OTg4MH0.ZugfDGQU7XeuxBA49Urc1B8kaEvMn_Y23Hk8OiwqhRQ'
f_token = 'tv5au3mo3dp1cghznzxokbqw545zbmdta6s4l45erukqfkfw0td74bt41ftgaos8252cb8cbcfb53967017448f922b184be86a24ef2748040de174c2b1a68b0b799397c48a11afabf34327fe67c03e6f985'

# Rentman API
rentman_url = "https://api.rentman.net/contacts"
rentman_headers = {'Authorization': token}

all_contacts = []
offset = 0
limit = 300  # Adjust if the API allows a larger limit

while True:
    params = {"offset": offset, "limit": limit}
    response = requests.get(rentman_url, headers=rentman_headers, params=params)
    
    if response.status_code != 200:
        print("Error fetching Rentman data:", response.text)
        break
    
    data = response.json()
    contacts = data.get("data", [])
    all_contacts.extend(contacts)  
    
    if len(contacts) < limit:
        break  # Stop when the last batch has fewer than `limit` contacts
    
    offset += limit  

# Extract Rentman names
rentman_names = {contact["displayname"] for contact in all_contacts}  

# FattureInCloud API - Fetch All Clients with Pagination
fic_url_base = "https://secure.fattureincloud.it/backend_apiV2/entities/clients?fieldset=fic_list&sort=name&page="
fic_headers = {
    'accept': 'application/json',
    'authorization': f_token
}

fic_clients = []
page = 1

while True:
    fic_url = f"{fic_url_base}{page}"
    fic_response = requests.get(fic_url, headers=fic_headers)
    
    if fic_response.status_code != 200:
        print("Error fetching FattureInCloud data:", fic_response.text)
        break

    data = fic_response.json()
    clients = data.get("data", [])
    
    if not clients:
        break  # No more clients to fetch, stop pagination
    
    fic_clients.extend(clients)
    page += 1  # Move to next page

# Identify matching clients
clients_to_delete = [client for client in fic_clients if client["name"] in rentman_names]
# Identify matching clients
clients_to_delete = [client for client in fic_clients if client["name"] in rentman_names]
print('clients_to_delete: ', clients_to_delete)

# Delete matching clients from FattureInCloud
delete_url_base = "https://secure.fattureincloud.it/backend_apiV2/entities/clients/"
for client in clients_to_delete:
    client_id = client["id"]
    delete_url = f"{delete_url_base}{client_id}"
    
    delete_response = requests.delete(delete_url, headers=fic_headers)
    if delete_response.status_code == 200:
        print(f"Deleted client: {client['name']} (ID: {client_id})")
    else:
        print(f"Error deleting client {client['name']} (ID: {client_id}): {delete_response.text}")