import requests
import json

token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoyMzUsImFjY291bnQiOiJuZXRpY2siLCJjbGllbnRfdHlwZSI6Im9wZW5hcGkiLCJjbGllbnQubmFtZSI6Im9wZW5hcGkiLCJleHAiOjIwNTU5MjI2ODAsImlzcyI6IntcIm5hbWVcIjpcImJhY2tlbmRcIixcInZlcnNpb25cIjpcIjQuNzE4LjAuMVwifSIsImlhdCI6MTc0MDM4OTg4MH0.ZugfDGQU7XeuxBA49Urc1B8kaEvMn_Y23Hk8OiwqhRQ'
f_token = 'tv5au3mo3dp1cghznzxokbqw545zbmdta6s4l45erukqfkfw0td74bt41ftgaos8252cb8cbcfb53967017448f922b184be86a24ef2748040de174c2b1a68b0b799397c48a11afabf34327fe67c03e6f985'

# Load contacts from JSON file instead of Rentman API
with open("customer_details.json", "r", encoding="utf-8") as file:
    all_contacts = json.load(file)

# Extract names from JSON
json_names = {contact["name"] for contact in all_contacts}

# FattureInCloud API
fic_url = "https://secure.fattureincloud.it/backend_apiV2/entities/clients?fieldset=fic_list&page=1&sort=name"
fic_headers = {
    'accept': 'application/json',
    'authorization': f_token
}

fic_response = requests.get(fic_url, headers=fic_headers)
if fic_response.status_code != 200:
    print("Error fetching FattureInCloud data:", fic_response.text)
    exit()

fic_clients = fic_response.json().get("data", [])
fic_names = {client["name"] for client in fic_clients}

# Find missing names
missing_names = json_names - fic_names
print(f'Missing clients to be created: {len(missing_names)}')

# Create missing clients in FattureInCloud
fic_create_url = "https://secure.fattureincloud.it/backend_apiV2/entities/clients"
for contact in all_contacts:
    if contact["name"] in missing_names:
        payload = {
            "data": {
                "name": contact["name"],
                "address_street" : f"{contact['address'].get('street', '')}{', ' if contact['address'].get('street') and contact['address'].get('street_number') else ''}{contact['address'].get('street_number', '')}",
                "address_postal_code": contact["address"].get("postal_code", ""),
                "address_city": contact["address"].get("city", ""),
                "address_province": contact["address"].get("province", ""),
                "address_country": contact["address"].get("country", ""),
                "vat_number": contact.get("vat_number", ""),
                "ei_code": contact["digital_invoicing"].get("recipient_code", "")
            }
        }

        # print('payload: ', payload)
        response = requests.post(fic_create_url, headers=fic_headers, json=payload)

        if response.status_code == 200:
            print(f"✅ Created client: {contact['name']}")
        else:
            print(f"❌ Failed to create client: {contact['name']}. Error: {response.text}")



































# # Rentman API
# rentman_url = "https://api.rentman.net/contacts"
# rentman_headers = {
#     'Authorization': token
# }

# all_contacts = []
# offset = 0
# limit = 300  # Adjust if the API allows a larger limit

# while True:
#     params = {"offset": offset, "limit": limit}
#     response = requests.get(rentman_url, headers=rentman_headers, params=params)
    
#     if response.status_code != 200:
#         print("Error fetching Rentman data:", response.text)
#         break
    
#     data = response.json()
#     contacts = data.get("data", [])
#     all_contacts.extend(contacts)  # Flatten list instead of appending lists
    
#     if len(contacts) < limit:
#         break  # Stop when the last batch has fewer than `limit` contacts
    
#     offset += limit  # Move to the next batch

# # Extract names
# rentman_names = {contact["displayname"] for contact in all_contacts}  # Convert to set

# # FattureInCloud API
# fic_url = "https://secure.fattureincloud.it/backend_apiV2/entities/clients?fieldset=fic_list&page=1&sort=name"
# fic_headers = {
#     'accept': 'application/json',
#     'authorization': f_token
# }

# fic_response = requests.get(fic_url, headers=fic_headers)
# if fic_response.status_code != 200:
#     print("Error fetching FattureInCloud data:", fic_response.text)
#     exit()

# fic_clients = fic_response.json().get("data", [])  # Extract client data
# fic_names = {client["name"] for client in fic_clients}  # Extract existing names

# # Find missing names
# missing_names = rentman_names - fic_names
# print(f'Missing clients to be created: {len(missing_names)}')

# # Create missing clients in FattureInCloud
# fic_create_url = "https://secure.fattureincloud.it/backend_apiV2/entities/clients"
# for contact in all_contacts:
#     if contact["displayname"] in missing_names and contact['tags'] != "fornitori":
#         payload = {
#             "data": {
#                 "name": contact["displayname"],
#                 "address_city": contact.get("visit_city", ""),
#                 "address_postal_code": contact.get("visit_postalcode", ""),
#                 "address_province": contact.get("visit_state", ""),
#                 "address_street": contact.get("visit_street", ""),
#                 # "code": contact.get("code", ""),
#                 "email": contact.get("email_1", ""),
#                 "first_name": contact.get("firstname", ""),
#                 "last_name": contact.get("surname", ""),
#                 "phone": contact.get("phone_1", ""),
#                 "vat_number": contact.get("VAT_code", ""),
#                 "tax_code": contact.get("fiscal_code", ""),
#             }
#         }
#         response = requests.post(fic_create_url, headers=fic_headers, json=payload)

#         if response.status_code == 200:
#             print(f"✅ Created client: {contact['displayname']}")
#         else:
#             print(f"❌ Failed to create client: {contact['displayname']}. Error: {response.text}")



