import requests
import os
from compare_customers import compare_names
from rentman_customer import get_rentman_customer_name
import json
from datetime import datetime

token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoyMzUsImFjY291bnQiOiJuZXRpY2siLCJjbGllbnRfdHlwZSI6Im9wZW5hcGkiLCJjbGllbnQubmFtZSI6Im9wZW5hcGkiLCJleHAiOjIwNTU5MjI2ODAsImlzcyI6IntcIm5hbWVcIjpcImJhY2tlbmRcIixcInZlcnNpb25cIjpcIjQuNzE4LjAuMVwifSIsImlhdCI6MTc0MDM4OTg4MH0.ZugfDGQU7XeuxBA49Urc1B8kaEvMn_Y23Hk8OiwqhRQ'
f_token = 'tv5au3mo3dp1cghznzxokbqw545zbmdta6s4l45erukqfkfw0td74bt41ftgaos8252cb8cbcfb53967017448f922b184be86a24ef2748040de174c2b1a68b0b799397c48a11afabf34327fe67c03e6f985'

projects_url = "https://api.rentman.net/projects"
invoice_url = "https://secure.fattureincloud.it/backend_apiV2/issued_documents"

# Headers for Rentman API
rentman_headers = {
    'Authorization': token  # Replace with your Rentman API token
}

# Headers for Fatture In Cloud API
invoice_headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'content-type': 'application/json; charset=UTF-8',
    'authorization': f_token  # Replace with your API key
}

# Variables
limit = 100
offset = 0
grouped_invoices = {}  # Store grouped projects per customer
record_count = 0  # Counter for records
MAX_RECORDS = 5  # Stop after 5 projects for testing

while record_count < MAX_RECORDS:
    params = {'limit': limit, 'offset': offset, 'fields': "name,id,customer"}
    response = requests.get(projects_url, headers=rentman_headers, params=params)

    if response.status_code == 200:
        data = response.json()
        projects = data['data']

        for project in projects:
            if record_count >= MAX_RECORDS:
                break  # Stop processing after 10 records

            project_id = project.get('id')
            # print('project_id: ', project_id)
            customer_id = project.get('customer', None)
            project_name = project.get('name', '').strip()

            if not customer_id:
                continue  # Skip projects with no customer

            # ✅ Get customer name
            customer_name = get_rentman_customer_name(token, customer_id)
            # print('customer_name: ', customer_name)
            # print(f"{projects_url}/{project_id}")
            project_cost_response = requests.get(f"{projects_url}/{project_id}", headers=rentman_headers)
            if project_cost_response.status_code == 200:
                project_cost_data = project_cost_response.json()
                # Ensure project_cost_data['data'] is a list and not empty
                if isinstance(project_cost_data['data'], list) and len(project_cost_data['data']) > 0:
                    first_cost_entry = project_cost_data['data'][0]  # Get the first item in the list
                    
                    customer_name['project_cost'] = {
                        "total_price": first_cost_entry.get('project_total_price', None),
                    }
                else:
                    customer_name['project_cost'] = {
                        "total_price": None,  
                    }
#             }
                # print('customer_name: ', customer_name)

#             # ✅ Group projects by customer
                if customer_id not in grouped_invoices:
                    grouped_invoices[customer_id] = {
                        "customer_name": customer_name.get('name', None),
                        "VAT_code": customer_name.get('VAT_code', None),
                        "visit_street": customer_name.get('visit_street', None),
                        "visit_city": customer_name.get('visit_city', None),
                        "visit_state": customer_name.get('visit_state', None),
                        "visit_postalcode": customer_name.get('visit_postalcode', None),
                        "country": customer_name.get('mailing_country', None),
                        "firstname": customer_name.get('firstname', None),
                        "surname": customer_name.get('surname', None),
                        "projects": []
                    }

                grouped_invoices[customer_id]["projects"].append(project)
                # grouped_invoices[customer_id]["total_sales"] += sales_price
                # grouped_invoices[customer_id]["total_purchase"] += purchase_price

                record_count += 1
            # print('grouped_invoices: ', grouped_invoices)

    else:
        break  # Exit loop if request fails

# ✅ Send grouped invoices to Fatture In Cloud
for customer_id, invoice in grouped_invoices.items():
    if invoice['country'] != "it":
        pass
    if invoice["VAT_code"] == "":
        pass
    print(f"\nCreating invoice for {invoice['customer_name']}...")

    # ✅ Convert projects into `items_list`
    items_list = []
    payments_list = []
    for proj in invoice["projects"]:
        dt_obj = datetime.fromisoformat(proj['created'])
        formatted_date = dt_obj.strftime("%Y-%m-%d")
        items_list.append({
            "id": -1,  # Placeholder ID
            "name": proj["name"],
            "code": "",
            "description": "",
            "qty": 1,
            "measure": "",
            "net_price": proj.get("project_cost", {}).get("total_price", 0) or 0,
            "gross_price": proj.get("project_cost", {}).get("total_price", 0) or 0,
            "vat": {
                "id": 0,
                "value": 22,
                "description": "IVA",
                "is_disabled": False
            },
            "discount": 0,
            "not_taxable": False,
            "apply_withholding_taxes": False,
            "stock": None,
            "stock_current": 0,
            "discount_highlight": False,
            "in_dn": True,
            "ei_raw": {},
            "is_empty_item": False
        })
        payments_list.append({
                "id": -1,
                "amount": proj.get("project_cost", {}).get("total_price", 0) or 0,
                "due_date": formatted_date,
                "payment_terms": {
                    "days": 0,
                    "type": "standard"
                },
                "status": "not_paid",
                "payment_account": "",
                "paid_date": formatted_date,
                "ei_raw": {}
            })
    
    
    # ✅ Prepare invoice payload
    invoice_payload = {
        "data": {
            "type": "invoice",
            "entity": {
                "country": "Italia",
                "default_discount": 0,
                "discount_highlight": False,
                "original_name": invoice.get("customer_name", ""),
                "entity_type": "client",
                "name": invoice.get("customer_name", ""),
                "code": "",
                "vat_number": invoice.get("VAT_code", ""),
                "tax_code": "",
                "address_street": invoice.get("visit_street", ""),
                "address_city": invoice.get("visit_city", ""),
                "address_province": invoice.get("visit_state", ""),
                "address_postal_code": invoice.get("visit_postalcode", ""),
                "address_extra": "",
                "first_name": invoice.get("firstname", ""),
                "last_name": invoice.get("surname", "")
            },
            "date": "2025-03-07",
            "language": {"code": "it"},
            "currency": {"id": "EUR", "symbol": "€"},
            "e_invoice": True,
            "items_list": items_list,
            "payments_list": payments_list,
            "payment_method": {
                "name": "Bonifico bancario",
                "is_default": True,
                "details": [
                    {
                        "title": "IBAN MPS",
                        "description": "IT10H0103032460000001702862"
                    },
                    {
                        "title": "Intestatario",
                        "description": "NK EVENTS SRL"
                    }
                ],
                "bank_name": "",
                "bank_beneficiary": "NK EVENTS SRL",
                "ei_payment_method": "MP05"
            }
            ,
        'ei_data': {
            'payment_method': 'MP05'  # FIX: Add this field
        }
        }
    }
    
    # print('invoice_payload: ', invoice_payload)
    # ✅ Post invoice to Fatture In Cloud
    response = requests.post(invoice_url, headers=invoice_headers, data=json.dumps(invoice_payload))

    if response.status_code == 200:
        print(f"✅ Invoice created successfully for {invoice['customer_name']}!")
    else:
        print(f"❌ Failed to create invoice for {invoice['customer_name']}: {response.text}")