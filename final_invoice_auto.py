import requests
import datetime as dt
from collections import defaultdict
from compare_customers import compare_names
import json
from datetime import datetime, timedelta
import re
from celery_app import app
import calendar
import os
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange

token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoyMzUsImFjY291bnQiOiJuZXRpY2siLCJjbGllbnRfdHlwZSI6Im9wZW5hcGkiLCJjbGllbnQubmFtZSI6Im9wZW5hcGkiLCJleHAiOjIwNTU5MjI2ODAsImlzcyI6IntcIm5hbWVcIjpcImJhY2tlbmRcIixcInZlcnNpb25cIjpcIjQuNzE4LjAuMVwifSIsImlhdCI6MTc0MDM4OTg4MH0.ZugfDGQU7XeuxBA49Urc1B8kaEvMn_Y23Hk8OiwqhRQ'
f_token = 'tv5au3mo3dp1cghznzxokbqw545zbmdta6s4l45erukqfkfw0td74bt41ftgaos8252cb8cbcfb53967017448f922b184be86a24ef2748040de174c2b1a68b0b799397c48a11afabf34327fe67c03e6f985'

months_it = {
    "January": "gennaio", "February": "febbraio", "March": "marzo",
    "April": "aprile", "May": "maggio", "June": "giugno",
    "July": "luglio", "August": "agosto", "September": "settembre",
    "October": "ottobre", "November": "novembre", "December": "dicembre"
}

# Mapping of normalized Rentman payment terms to invoice text
payment_term_mapping = {
    "rimessa diretta": "Rimessa Diretta",
    "come da contratto": "100% a 30 gg dffm",
    "100% a 30gg dffm": "100% a 30gg dffm",
    "50 % a 30 gg dffm - 50 % a 60 gg dffm": "50 % a 30 gg dffm - 50 % a 60 gg dffm",
    "100% a 60gg dffm": "100% a 60gg dffm",
    "50% alla sottoscrizione + 50% a 30gg dffm": "50% alla sottoscrizione + 50% a 30gg dffm",
    "50% alla sottoscrizione + 50% a 60gg dffm": "50% alla sottoscrizione + 50% a 60gg dffm",
    "100% alla sottoscrizione": "100% alla sottoscrizione Prima dell Evento",
    "30% alla sottoscrizione + 70% a 30gg dffm": "30% alla sottoscrizione + 70% a 30gg dffm",
    "40% alla sottoscrizione + 60% a 60gg dffm": "40% alla sottoscrizione + 60% a 60gg dffm",
    "30% alla sottoscrizione + 70% a 60gg dffm": "30% alla sottoscrizione + 70% a 60 gg dffm",
    "50% alla sottoscrizione + saldo a 10 gg dall'evento": "50% alla sottoscrizione + saldo a 10 gg dall'evento",
    "40% alla sottoscrizione + 60% a 30gg dffm": "40% alla sottoscrizione + 60% a 30gg dffm",
    "30% alla sottoscrizione + saldo a 10 gg dall'evento": "30% alla sottoscrizione + saldo a 10 gg dall'evento",
    "50% alla sottoscrizione + 50% a fine evento": "50% alla sottoscrizione + 50% a fine evento",
}

def calculate_due_dates(payment_condition: str, invoice_date: dt.date, event_date: dt.date = None):
    print('payment_condition: ', payment_condition)
    due_dates = []
    if "100% alla sottoscrizione" in payment_condition.lower():
        # In this case, the payment is due immediately, so we use the invoice date as the due date
        return [{"percentage": 100, "due_date": invoice_date}]

    # Extract pattern like "50% a 30 gg" or "100% a 60 gg"
    pattern = re.findall(r'(\d+)%.*?(\d+)?\s?gg', payment_condition.lower())

    if not pattern:
        if "rimessa diretta" in payment_condition.lower():
            return [{"percentage": 100, "due_date": invoice_date}]
        elif "come da contratto" in payment_condition.lower():
            return [{"percentage": 100, "due_date": None}]
        else:
            return [{"percentage": 100, "due_date": None}]

    for perc_str, days_str in pattern:
        percentage = int(perc_str)
        days = int(days_str) if days_str else 0

        # Determine base date (invoice or event-related)
        if "evento" in payment_condition.lower() and event_date:
            base_date = event_date
        else:
            base_date = invoice_date

        due_date = base_date + dt.timedelta(days=days)

        due_dates.append({
            "percentage": percentage,
            "due_date": due_date
        })

    return due_dates

# Rentman API details
BASE_URL = "https://api.rentman.net"
# Replace 'token' with your Rentman API token
HEADERS = {'Authorization': token}

invoice_url = "https://secure.fattureincloud.it/backend_apiV2/issued_documents"
invoice_headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'content-type': 'application/json; charset=UTF-8',
    'authorization': f_token
}

LIMIT = 100  # Pagination limit
MAX_RECORDS = 5
INVOICE_DATA_FILE = "second_invoices.json" #Added a constant for the filename

# def get_projects():
#     """Fetch projects created in the last 30 days with pagination."""
#     offset = 0
#     projects = []
    
#     # Calculate the date 30 days ago
#     thirty_days_ago = (dt.datetime.now() - dt.timedelta(days=30)).isoformat()

#     # while len(projects) < MAX_RECORDS:
#     while True:
#         params = {'limit': LIMIT, 'offset': offset, 'fields': "name,id,customer,created,usageperiod_end,custom"}
#         response = requests.get(f"{BASE_URL}/projects", headers=HEADERS, params=params)

#         if response.status_code == 200:
#             data = response.json().get("data", [])
#             for project in data:
#                 created_date = project.get("created")
                
#                 # Ensure project is within the last 30 days
#                 if created_date and created_date >= thirty_days_ago:
#                     custom_dates = project.get("custom")
#                     projects.append({
#                         "id": project.get("id"),
#                         "name": project.get("name"),
#                         "customer": project.get("customer"),
#                         "usageperiod_end": project.get("usageperiod_end"),
#                         "start_date": custom_dates['custom_10'],
#                         "end_date": custom_dates['custom_11'],
#                         "created_date": created_date
#                     })
#                 # if len(projects) >= MAX_RECORDS:
#                 #     break  # Stop if we reach the max limit for testing
                
#             if len(data) < LIMIT:
#                 break  # Stop if we get fewer results than the limit
#         else:
#             print(f"Error fetching projects: {response.status_code}, {response.text}")
#             break
        
#         offset += LIMIT  # Increase pagination offset

#     return projects

def get_projects():
    """Fetch projects where start and end date are within the current month."""
    offset = 0
    projects = []
    
    # Get first and last day of the current month
    # today = dt.datetime.today()
    # first_day = dt.datetime(today.year, today.month, 1).isoformat()
    # print('first_day: ', first_day)
    # last_day = dt.datetime(today.year, today.month + 1, 1) - dt.timedelta(days=1)
    # last_day = last_day.isoformat()
    # print('last_day: ', last_day)
    
    while True:
        params = {'limit': LIMIT, 'offset': offset, 'fields': "name,id,customer,created,usageperiod_end,usageperiod_start,reference,custom"}
        response = requests.get(f"{BASE_URL}/projects", headers=HEADERS, params=params)

        if response.status_code == 200:
            data = response.json().get("data", [])
            for project in data:
                custom_dates = project.get("custom", {})
                start_date = custom_dates.get('custom_10')
                end_date = custom_dates.get('custom_11')
                if start_date and end_date:
                    today = dt.datetime.today()
                    start_date_obj = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_date_obj = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
                    first_day_obj = dt.datetime(today.year, today.month, 1).date()
                    last_day_obj = (dt.datetime(today.year, today.month + 1, 1) - dt.timedelta(days=1)).date()

                    if first_day_obj <= start_date_obj <= last_day_obj and first_day_obj <= end_date_obj <= last_day_obj:
                        projects.append({
                            "id": project.get("id"),
                            "name": project.get("name"),
                            "customer": project.get("customer"),
                            "usageperiod_end": project.get("usageperiod_end"),
                            "usageperiod_start": project.get("usageperiod_start"),
                            "start_date": start_date,
                            "end_date": end_date,
                            "reference": project.get("reference"),
                            "created_date": project.get("created")
                        })
                    # print('projects: ', projects)
                
            if len(data) < LIMIT:
                break  # Stop if we get fewer results than the limit
        else:
            print(f"Error fetching projects: {response.status_code}, {response.text}")
            break
        
        offset += LIMIT  # Increase pagination offset

    return projects

def get_subprojects_by_project(project_id):
    """Fetch sub-projects related to a project."""
    response = requests.get(f"{BASE_URL}/subprojects?project={project_id}", headers=HEADERS)

    if response.status_code == 200:
        return [
            {"name": sub.get("displayname"), "id": sub.get("id")}
            for sub in response.json().get("data", [])
        ]
    
    return []


def get_quotes_by_project(project_id):
    """Fetch the most recent quote related to a project."""
    response = requests.get(f"{BASE_URL}/quotes?project={project_id}", headers=HEADERS)

    if response.status_code == 200:
        quotes = response.json().get("data", [])
        if not quotes:
            return []

        # Sort quotes by 'modified' date (fallback to 'created' if needed)
        quotes.sort(key=lambda q: q.get("modified") or q.get("created"), reverse=True)

        latest_quote = quotes[0]  # Get the most recent one

        return [{
            "number": latest_quote.get("number"),
            "name": latest_quote.get("displayname"),
            "id": latest_quote.get("id"),
            "price": latest_quote.get("price", 0),
        }]

    return []

def get_project_prices(project_id):
    """Fetches project details from Rentman API and extracts price-related information."""
    url = f"https://api.rentman.net/projects/{project_id}"
    headers = {"Authorization": token}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", {})

        price_details = {
            "project_total_price": data.get("project_total_price", 0),
            "project_rental_price": data.get("project_rental_price", 0),
            "project_sale_price": data.get("project_sale_price", 0),
            "project_crew_price": data.get("project_crew_price", 0),
            "project_transport_price": data.get("project_transport_price", 0),
            "project_other_price": data.get("project_other_price", 0),
            "project_insurance_price": data.get("project_insurance_price", 0),
            "already_invoiced": data.get("already_invoiced", 0),
        }

        return price_details

    except requests.exceptions.RequestException as e:
        print(f"Error fetching project details: {e}")
        return None

def create_invoice(invoice_payload):
    print('invoice_payload: ', invoice_payload)
    today_date = datetime.today().strftime('%Y-%m-%d')
    print('today_date: ', today_date)

    # # Extract and remove due_date
    due_date = invoice_payload['data'].pop('due_date', '')

    # # Check if today is the due date
    # if today_date == due_date:

    response = requests.post(invoice_url, headers=invoice_headers, data=json.dumps(invoice_payload))

    if response.status_code == 200:
        print("Invoice created successfully!")
    else:
        print(f"Error creating invoice: {response.status_code}, {response.text}")
    # else:
        print(f"Skipping invoice creation. Today ({today_date}) is not the due date ({due_date}).")

def extract_id(contact_path):
    """Extract numeric ID from contact path."""
    return re.search(r'/contacts/(\d+)', contact_path).group(1) if contact_path else None

def load_payment_terms():
    import os
    import json

    json_path = "customer_payment_terms.json"
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} not found")
    with open(json_path, "r") as file:
        return {str(entry["id"]): entry for entry in json.load(file)}

payment_terms_data = load_payment_terms()

# Load customer data once at the start
def load_customers_from_json(path="customer_details.json"):
    with open(path, "r", encoding="utf-8") as file:
        return {str(customer["id"]): customer for customer in json.load(file)}

# Get customer data from the loaded JSON
def get_rentman_customer_name(customer_id, customers_data):
    return customers_data.get(str(extract_id(customer_id)), {})

def save_second_invoice_data(data):
    """Appends unique invoice data to the JSON file as a list."""
    try:
        # Load existing data
        if os.path.exists(INVOICE_DATA_FILE):
            with open(INVOICE_DATA_FILE, "r") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    existing_data = [existing_data]
        else:
            existing_data = []

        # Avoid duplicates
        if data not in existing_data:
            existing_data.append(data)

        # Save updated list
        with open(INVOICE_DATA_FILE, "w") as f:
            json.dump(existing_data, f, indent=4)

    except Exception as e:
        print(f"Error saving second invoice data: {e}")

def load_second_invoice_data():
    """Loads the second invoice data from the JSON file."""
    if not os.path.exists(INVOICE_DATA_FILE):
        return {}  # Return empty dict if file does not exist
    try:
        with open(INVOICE_DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading second invoice data: {e}")
        return {}  # Return empty dict on error to prevent crashing

def clear_second_invoice_data():
    """Clears the second invoice data from the JSON file."""
    if os.path.exists(INVOICE_DATA_FILE):
        try:
            os.remove(INVOICE_DATA_FILE)
            print("Second invoice data file cleared.")
        except Exception as e:
            print(f"Error clearing second invoice data file: {e}")

def get_due_date(payment_term: str, invoice_date: datetime, event_date: datetime) -> datetime:
    payment_term = payment_term.lower()

    def days_from_invoice(days):
        return (invoice_date + timedelta(days=days)).date()

    def days_before_event(days):
        return (event_date - timedelta(days=days)).date()

    if "100% a 30gg" in payment_term:
        return days_from_invoice(30)
    elif "100% a 60gg" in payment_term:
        return days_from_invoice(60)
    elif "100% alla sottoscrizione" in payment_term:
        return invoice_date.date()
    elif "30% alla sottoscrizione" in payment_term:
        if "70% a 30gg" in payment_term:
            return days_from_invoice(30)
        elif "70% a 60gg" in payment_term:
            return days_from_invoice(60)
        elif "saldo a 10 gg dall'evento" in payment_term:
            return days_before_event(10)
        else:
            return invoice_date.date()
    elif "40% alla sottoscrizione" in payment_term:
        if "60% a 30gg" in payment_term:
            return days_from_invoice(30)
        elif "60% a 60gg" in payment_term:
            return days_from_invoice(60)
        else:
            return invoice_date.date()
    elif "50% alla sottoscrizione" in payment_term:
        if "50% a 30gg" in payment_term:
            return days_from_invoice(30)
        elif "50% a 60gg" in payment_term:
            return days_from_invoice(60)
        elif "50% a fine evento" in payment_term:
            return event_date.date()
        elif "saldo a 10 gg dall'evento" in payment_term:
            return days_before_event(10)
        else:
            return invoice_date.date()
    else:
        # Default case: set to 3rd of next month
        next_month = invoice_date.replace(day=28) + timedelta(days=4)
        third_next_month = next_month.replace(day=3)
        return third_next_month.date()

def process_second_invoices():  
    today_str = dt.date.today().isoformat()

    pending = load_second_invoice_data()
    print('pending: ', pending)

    still_pending = []

    for entry in pending:
        print('entry: ', entry)
        print('entry["invoice_date"]: ', entry["invoice_date"])
        if entry["invoice_date"] == today_str:
            # SECOND INVOICE: 60%
            payments_list = [{
                "id": -1,
                "amount": entry["amount"],
                "due_date": entry["due_date"],
                "payment_terms": {"days": 30, "type": "standard"},
                "status": "not_paid"
            }]

            invoice_payload = {
                "data": {
                    "type": "invoice",
                    "due_date": entry["due_date"],
                    "entity": entry["entity"],
                    "language": {"code": "it"},
                    "currency": {"id": "EUR", "symbol": "€"},
                    "e_invoice": True,
                    "ei_data":{
                            "bank_beneficiary":"NK EVENTS SRL",
                            "bank_name":"IT76I0313801600000013394747",
                            "cig":"",
                            "cup":"",
                            "od_date":"2025-05-08",
                            "od_number":"",
                            "original_document_type":"",
                            "payment_method":"MP05",
                            "vat_kind":"I",
                            "invoice_date":"2025-05-08",
                            "invoice_number":""
                            },
                    "items_list": entry["items_list"],
                    "payments_list": payments_list,
                    "show_payment_method": True,
                    "payment_method": {
                        "name": "Bonifico bancario",
                        "is_default": True,
                        "ei_payment_method": "MP05"
                    }
                }
            }

            print("✅ SECOND invoice payload:", invoice_payload)
            # create_invoice(invoice_payload)
        else:
            still_pending.append(entry)

    # Overwrite file with still-pending invoices
    with open(INVOICE_DATA_FILE, "w") as f:
        json.dump(still_pending, f, indent=2)

def get_fattureincloud_client_default_discount(client_name):
    base_url = "https://secure.fattureincloud.it/backend_apiV2/entities/clients"
    
    common_headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "it",
        "authorization": "tv5au3mo3dp1cghznzxokbqw545zbmdta6s4l45erukqfkfw0td74bt41ftgaos8252cb8cbcfb53967017448f922b184be86a24ef2748040de174c2b1a68b0b799397c48a11afabf34327fe67c03e6f985",
        "cache-control": "no-cache",
        "content-type": "application/json; charset=utf-8",
        "pragma": "no-cache",
        "x-device-id": "Gr6U521KpJV8BoP4kMPrzXaaanFyGbpNKJVmEqX0tcjlZQBnIjIjBFfqIlR3hgQu",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://secure.fattureincloud.it/clients",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }

    # Step 1: Get client by name
    params = {
        "fieldset": "fic_list",
        "page": 1,
        "filter[0][field]": "name",
        "filter[0][op]": "contains",
        "filter[0][value]": client_name,
        "sort": "name"
    }

    response = requests.get(base_url, headers=common_headers, params=params)
    if response.status_code != 200:
        print("FIC API search error:", response.status_code, response.text)
        return None

    clients = response.json().get("data", [])
    if not clients:
        print("No client found with name:", client_name)
        return None

    client_id = clients[0]["id"]

    # Step 2: Get detailed client data
    detail_url = f"{base_url}/{client_id}"
    detail_params = {"fieldset": "detailed"}

    detail_response = requests.get(detail_url, headers=common_headers, params=detail_params)
    if detail_response.status_code != 200:
        print("FIC API detail error:", detail_response.status_code, detail_response.text)
        return None

    client_data = detail_response.json().get("data", {})
    return client_data.get("default_discount")


@app.task(name='final_invoice_auto')
def main():
    """Main execution function."""
    try:
        projects = get_projects()
        customers_data = load_customers_from_json()
    except FileNotFoundError:
        print("customer_payment_terms.json not found!")
        return
    grouped_invoices = {}
    second_invoice_data = {} # Dictionary to store second invoice data

    for project in projects:
        project_id = project["id"]
        customer_id = project["customer"]
        start_date_obj = datetime.fromisoformat(project['usageperiod_start'])
        formatted_start_date = start_date_obj.strftime("%Y-%m-%d")
        end_date_obj = datetime.fromisoformat(project['usageperiod_end'])
        formatted_date = end_date_obj.strftime("%Y-%m-%d")
        project_name = project["name"]

        if not customer_id:
            continue

        customer_data = get_rentman_customer_name(customer_id, customers_data)
        customer_name = customer_data.get("name", "Unknown Customer")
        # print('customer_name: ', customer_name)
        # fic_clients = get_fattureincloud_client_by_name(customer_name)

        subprojects = get_subprojects_by_project(project_id)
        quotes = get_quotes_by_project(project_id)
        # print('quotes: ', quotes)
        
        # total_quote_price = sum(q["price"] for q in quotes)

        if customer_id not in grouped_invoices:
            address = customer_data.get("address", {})
            digital_invoice = customer_data.get("digital_invoicing", {})
            grouped_invoices[customer_id] = {
                "customer_name": customer_data.get("name", None),
                "VAT_code": customer_data.get("vat_number", None),
                "visit_street": address.get("street", "") +" "+ address.get("street_number", ""),
                "visit_city": address.get("city", None),
                "visit_state": address.get("province", None),
                "visit_postalcode": address.get("postal_code", None),
                "country": address.get("country", None),
                "code": digital_invoice.get("recipient_code", ""),
                "projects": []
            }

        grouped_invoices[customer_id]["projects"].append({
            "id": project_id,
            "name": project_name,
            "event_start_date": project['usageperiod_start'],
            "event_end_date": project['usageperiod_end'],
            "start_date": project['start_date'],
            "end_date": project['end_date'],
            "total_price": 0,
            "subprojects": subprojects,
            "quotes": quotes,
            "reference": project['reference'],
            "created_date": project["created_date"] 
        })
        # print('grouped_invoices: ', grouped_invoices)

    # Send invoices
    for customer_id, invoice in grouped_invoices.items():
        # print('invoice: ', invoice)
        # if invoice['country'] != "it" or not invoice["VAT_code"]:
        if not invoice["VAT_code"]:
            continue
        print(f"\nCreating invoice(s) for {invoice['customer_name']}...")
        discount = get_fattureincloud_client_default_discount(invoice['customer_name'])
        payment_term_obj = payment_terms_data.get(extract_id(customer_id), {})
        payment_term = payment_term_obj.get("payment_term", "default").lower()
        billing_date = payment_term_obj.get("billing_date", "N/A")
        items_list = []
        total_invoice_amount = 0
        kk = []
        sorted_projects = sorted(invoice["projects"], key=lambda x: datetime.fromisoformat(x["event_start_date"]))
        for proj in sorted_projects:
            project_price = get_project_prices(proj['id'])
            total_price = project_price['project_total_price']
            if total_price == 0:
                continue
            t_amount = round(float(project_price['project_total_price']), 2)
            quote_numbers = ", ".join(
                    q['number'] for q in proj.get('quotes', [])
                    if q.get('number', '').endswith('-')
            )
            subproject_names = " \\ ".join(sp['name'] for sp in proj.get('subprojects', []))
            
            # event_date = datetime.strptime(proj['start_date'], "%Y-%m-%d")
            # invoice_date = datetime.now()
            # due_date = get_due_date(payment_term, invoice_date, proj['end_date'])
            start_date = datetime.strptime(proj["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(proj["end_date"], "%Y-%m-%d")
            month_name = months_it[end_date.strftime("%B")]
            formatted_date = f"{start_date.day}-{end_date.day} {month_name} {end_date.year}"
            # if project_price['project_total_price'] == 0:
            #     pass


            items_list.append({
                "id": -1,
                "name":  f"{proj['name']} ({formatted_date})  Numero preventivo {quote_numbers}" + \
                            (f" PO:{proj['reference']}" if proj['reference'] else ""),
                "qty": 1,
                "net_price": float(total_price),
                "gross_price": float(total_price),
                # "description": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}",
                "vat": {
                    "id": 0,
                    "value": 22,
                    "description": "IVA",
                    "is_disabled": False
                },
                "discount": discount or 0 ,
                "not_taxable": False,
                "end_date": proj["end_date"]
            })
        #     print(proj["name"])
        #     print('ddddddddddddddddddddddddd: ', round(float(project_price['project_total_price']), 2))
            total_invoice_amount += float(total_price)
        # print(round(total_invoice_amount, 2))
        print('billing_date: ', billing_date)
        print('payment_term: ', payment_term)

        if billing_date == "Fattura a fine Lavoro":
            print('items_list1111111111111111111: ', items_list)
            items_list = [
                item for item in items_list
                if re.search(r'Numero preventivo \d{4}-', item['name'])
            ]
            print('ssssssssssssssssssssss: ', items_list)
            if items_list:
                total_price = sum(item['net_price'] for item in items_list)
                latest_end_date = max(
                    datetime.strptime(item['end_date'], "%Y-%m-%d") for item in items_list
                )
                net_total = 0
                for item in items_list:
                    item.pop("end_date", None)  # Remove if present
                    item["discount"] = discount or 0  # Apply client discount
                    discounted_price = round(item["net_price"] * (1 - item["discount"] / 100), 2)
                    net_total += discounted_price

                net_total = round(net_total, 2)
                print('net_total: ', net_total)
                vat_amount = round(net_total * 0.22, 2)
                print('vat_amount: ', vat_amount)
                gross_total = round(net_total * 1.22, 2)
                print('gross_total: ', gross_total)
                # Invoice is issued the day after the event end date.
                # Move to the 1st day of the next month
                if end_date_obj.month == 12:
                    invoice_date = end_date_obj.replace(year=end_date_obj.year + 1, month=1, day=1)
                else:
                    invoice_date = end_date_obj.replace(month=end_date_obj.month + 1, day=1)

                print('invoice_date:', invoice_date)

                # Due date is 30 days after invoice_date
                due_date = invoice_date + timedelta(days=30)
                print('due_date:', due_date)
                # print('dt.date.today(): ', dt.date.today(), type(dt.date.today()))
                # print('invoice_date.date(): ', invoice_date.date(), type(invoice_date.date()))
                print('latest_end_date: ', latest_end_date)
                for item in items_list:
                    item.pop("end_date", None)
                if dt.date.today() == invoice_date.date():
                    aaa = calculate_due_dates(payment_term, invoice_date, latest_end_date)
                    due_date = ''
                    for d in aaa:
                        due_date = d['due_date']
                    # print('aaa1111111111111111111111111111111111: ', due_date)
                    payments_list = [{
                        "id": -1,
                        "amount": gross_total,
                        "due_date": due_date.strftime("%Y-%m-%d"),
                        "payment_terms": {"days": 30, "type": "standard"},
                        "status": "not_paid"
                    }]
                    # print('invoice: ', invoice)
                    invoice_payload = {
                        "data": {
                            "type": "invoice",
                            "due_date": due_date.strftime("%Y-%m-%d"),
                            "entity": {
                                "country": "Italia",
                                "name": invoice.get("customer_name", ""),
                                "vat_number": invoice.get("VAT_code", ""),
                                "address_street": invoice.get("visit_street", ""),
                                "address_city": invoice.get("visit_city", ""),
                                "address_province": invoice.get("visit_state", ""),
                                "address_postal_code": invoice.get("visit_postalcode", ""),
                                "first_name": invoice.get("firstname", ""),
                                "last_name": invoice.get("surname", ""),
                                "ei_code": invoice.get("code", ""),
                                # "address_extra": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}"
                            },
                            # "date": invoice_date.strftime("%Y-%m-%d"),
                            "language": {
                                "code": "it",
                                "name": "Italiano"
                                },
                            "currency": {"id": "EUR", "symbol": "€"},
                            "e_invoice": True,
                            "ei_data":{
                                "bank_beneficiary":"NK EVENTS SRL",
                                "bank_name":"IT76I0313801600000013394747",
                                "cig":"",
                                "cup":"",
                                "od_date":"2025-05-08",
                                "od_number":"",
                                "original_document_type":"",
                                "payment_method":"MP05",
                                "vat_kind":"I",
                                "invoice_date":"2025-05-08",
                                "invoice_number":""
                                },
                            "items_list": items_list,
                            "payments_list": payments_list,
                            "show_payment_method": True,
                            "payment_method": {
                                    "name": "Bonifico bancario",
                                    "is_default": False,
                                    "details": [
                                        {
                                            "title": "BANCA REALE",
                                            "description": "IT76I0313801600000013394747"
                                        },
                                        {
                                            "title": "Intestatario",
                                            "description": "NK EVENTS SRL"
                                        },
                                        {
                                            "title": "Bic/Swift",
                                            "description": "BRTOITTT"
                                        }
                                    ],
                                    "bank_iban": "IT76I0313801600000013394747",
                                    "bank_name": "IT76I0313801600000013394747",
                                    "bank_beneficiary": "NK EVENTS SRL",
                                    "ei_payment_method": "MP05",
                                    "label": "Bonifico bancario - IT76I0313801600000013394747"
                                },
                                "options": {
                                    "fix_payments": True
                                }
                        }
                    }
                    # print('invoice_payload: ', invoice_payload)
                    create_invoice(invoice_payload)
            
        elif billing_date == "Fattura Fine Mese":
            print('items_list2222222222222222222: ', items_list)
            items_list = [
                item for item in items_list
                if re.search(r'Numero preventivo \d{4}-', item['name'])
            ]
            print('llllllllllllllllllllllll: ', items_list)
            if items_list:
                latest_end_date = max(
                    datetime.strptime(item['end_date'], "%Y-%m-%d") for item in items_list
                )
                net_total = 0
                for item in items_list:
                    item.pop("end_date", None)  # Remove if present
                    item["discount"] = discount or 0  # Apply client discount
                    discounted_price = round(item["net_price"] * (1 - item["discount"] / 100), 2)
                    net_total += discounted_price

                net_total = net_total
                vat_amount = round(net_total * 0.22, 2)
                gross_total = round(net_total * 1.22, 2)
                total_price = sum(item['net_price'] for item in items_list)
                # invoice_due_date = latest_end_date + timedelta(days=1)
                # next_month = invoice_due_date + relativedelta(months=1)
                # due_date = next_month.replace(day=3)
                year = latest_end_date.year
                month = latest_end_date.month
                last_day = monthrange(year, month)[1]
                last_date = date(year, month, last_day)
                print('last_day: ', last_day)
                due_date = latest_end_date.replace(day=last_day)
                for item in items_list:
                    item.pop("end_date", None)
                if dt.date.today() == last_date:
                    aaa = calculate_due_dates(payment_term, due_date, latest_end_date)
                    due_date = ''
                    for d in aaa:
                        due_date = d['due_date'].date().strftime('%Y-%m-%d')
                    print('due_date: ', due_date)
                    payments_list = [{
                        "id": -1,
                        "amount": gross_total,
                        "due_date": due_date,
                        "payment_terms": {"days": 30, "type": "standard"},
                        "status": "not_paid"
                    }]
                    invoice_payload = {
                        "data": {
                            "type": "invoice",
                            "due_date": due_date,
                            "entity": {
                                "country": "Italia",
                                "name": invoice.get("customer_name", ""),
                                "vat_number": invoice.get("VAT_code", ""),
                                "address_street": invoice.get("visit_street", ""),
                                "address_city": invoice.get("visit_city", ""),
                                "address_province": invoice.get("visit_state", ""),
                                "address_postal_code": invoice.get("visit_postalcode", ""),
                                "first_name": invoice.get("firstname", ""),
                                "last_name": invoice.get("surname", ""),
                                "ei_code": invoice.get("code", ""),
                                # "address_extra": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}"
                            },
                            "language": {"code": "it"},
                            "currency": {"id": "EUR", "symbol": "€"},
                            "e_invoice": True,
                            "ei_data":{
                                "bank_beneficiary":"NK EVENTS SRL",
                                "bank_name":"IT76I0313801600000013394747",
                                "cig":"",
                                "cup":"",
                                "od_date":"2025-05-08",
                                "od_number":"",
                                "original_document_type":"",
                                "payment_method":"MP05",
                                "vat_kind":"I",
                                "invoice_date":"2025-05-08",
                                "invoice_number":""
                            },
                            "items_list": items_list,
                            "payments_list": payments_list,
                            "show_payment_method": True,
                            "payment_method": {
                                    "name": "Bonifico bancario",
                                    "is_default": False,
                                    "details": [
                                        {
                                            "title": "BANCA REALE",
                                            "description": "IT76I0313801600000013394747"
                                        },
                                        {
                                            "title": "Intestatario",
                                            "description": "NK EVENTS SRL"
                                        },
                                        {
                                            "title": "Bic/Swift",
                                            "description": "BRTOITTT"
                                        }
                                    ],
                                    "bank_iban": "IT76I0313801600000013394747",
                                    "bank_name": "IT76I0313801600000013394747",
                                    "bank_beneficiary": "NK EVENTS SRL",
                                    "ei_payment_method": "MP05",
                                    "label": "Bonifico bancario - IT76I0313801600000013394747"
                                }
                        },
                        "options": {
                            "fix_payments": True
                        }
                    }
                    # print('invoice_payload: ', invoice_payload)
                    create_invoice(invoice_payload)
            
        elif billing_date == "100% Alla Conferma":
            print('items_list3333333333333333333333333: ', items_list)
            items_list = [
                item for item in items_list
                if re.search(r'Numero preventivo \d{4}-', item['name'])
            ]
            print('cccccccccccccccccccooooooooooooooo: ', items_list)
            total_price = sum(item['net_price'] for item in items_list)
            # print('total_net_price: ', total_net_price)
            if items_list:
                start_date_obj = datetime.fromisoformat(project['usageperiod_start'])
                invoice_date = start_date_obj - dt.timedelta(days=1)
                print('invoice_date: ', invoice_date)
                due_date = invoice_date + dt.timedelta(days=30)
                for item in items_list:
                    item.pop("end_date", None)
                # if dt.date.today() == invoice_date.date():
                aaa = calculate_due_dates(payment_term, invoice_date)
                due_date = ''
                for d in aaa:
                    due_date = d['due_date']
                # invoice_date is a datetime object
                year = due_date.year
                month = due_date.month
                last_day = monthrange(year, month)[1]  # Get the last day of the month

                # Construct full last date of the month (with time if needed)
                due_date1 = due_date.replace(day=last_day)
                payments_list = [{
                    "id": -1,
                    "amount": round((total_price) * 1.22, 2),
                    "due_date": due_date1.strftime("%Y-%m-%d"),
                    "payment_terms": {"days": 30, "type": "standard"},
                    "status": "not_paid"
                }]
                invoice_payload = {
                    "data": {
                        "type": "invoice",
                        "due_date": due_date1.strftime("%Y-%m-%d"),
                        "entity": {
                            "country": "Italia",
                            "name": invoice.get("customer_name", ""),
                            "vat_number": invoice.get("VAT_code", ""),
                            "address_street": invoice.get("visit_street", ""),
                            "address_city": invoice.get("visit_city", ""),
                            "address_province": invoice.get("visit_state", ""),
                            "address_postal_code": invoice.get("visit_postalcode", ""),
                            "first_name": invoice.get("firstname", ""),
                            "last_name": invoice.get("surname", ""),
                            "ei_code": invoice.get("code", ""),
                            # "address_extra": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}"
                        },
                        "language": {"code": "it"},
                        "currency": {"id": "EUR", "symbol": "€"},
                        "e_invoice": True,
                        "ei_data":{
                            "bank_beneficiary":"NK EVENTS SRL",
                            "bank_name":"IT76I0313801600000013394747",
                            "cig":"",
                            "cup":"",
                            "od_date":"2025-05-08",
                            "od_number":"",
                            "original_document_type":"",
                            "payment_method":"MP05",
                            "vat_kind":"I",
                            "invoice_date":"2025-05-08",
                            "invoice_number":""
                        },
                        "items_list": items_list,
                        "payments_list": payments_list,
                        "show_payment_method": True,
                        "payment_method": {
                                "name": "Bonifico bancario",
                                "is_default": False,
                                "details": [
                                    {
                                        "title": "BANCA REALE",
                                        "description": "IT76I0313801600000013394747"
                                    },
                                    {
                                        "title": "Intestatario",
                                        "description": "NK EVENTS SRL"
                                    },
                                    {
                                        "title": "Bic/Swift",
                                        "description": "BRTOITTT"
                                    }
                                ],
                                "bank_iban": "IT76I0313801600000013394747",
                                "bank_name": "IT76I0313801600000013394747",
                                "bank_beneficiary": "NK EVENTS SRL",
                                "ei_payment_method": "MP05",
                                "label": "Bonifico bancario - IT76I0313801600000013394747"
                            },
                        "options": {
                            "fix_payments": True
                        }
                    }
                }
                # print('invoice_payload: ', invoice_payload)
                create_invoice(invoice_payload)
        
        elif billing_date == "Fattura Acconto 40 Alla Conferma":
            print('items_list44444444444444444444444: ', items_list)
            items_list = [
                item for item in items_list
                if re.search(r'Numero preventivo \d{4}-', item['name'])
            ]
            print('aaaaaaaaaaaaaaaaaaaaaalllllllllllllll: ', items_list)
            total_price = round(float(sum(item['net_price'] for item in items_list)), 2)
            if items_list:
                start_date_obj = datetime.fromisoformat(project['usageperiod_start'])
                end_date_obj = datetime.fromisoformat(project['usageperiod_end'])

                invoice_date = dt.date.today()
                due_date = invoice_date + dt.timedelta(days=30)
                second_invoice_date = end_date_obj + dt.timedelta(days=1)
                second_due_date = second_invoice_date + dt.timedelta(days=30)
                for item in items_list:
                    item.pop("end_date", None)
                # if dt.date.today() == invoice_date.date():
                print('invoice_date.date(): ', invoice_date)
                # FIRST INVOICE: 40%
                first_invoice_amount = int(round(total_price * 0.4))
                aaa = calculate_due_dates(payment_term, invoice_date)
                due_date = ''
                for d in aaa:
                    due_date = d['due_date']

                print('due_date: ', due_date)
                year = due_date.year
                month = due_date.month
                last_day = monthrange(year, month)[1]  # Get the last day of the month

                # Construct full last date of the month (with time if needed)
                due_date1 = due_date.replace(day=last_day)
                print('due_date1:', due_date1)
                payments_list = [{
                    "id": -1,
                    "amount": first_invoice_amount,
                    "due_date": due_date1.strftime("%Y-%m-%d"),
                    "payment_terms": {"days": 30, "type": "standard"},
                    "status": "not_paid"
                }]

                entity_data = {
                    "country": "Italia",
                    "name": invoice.get("customer_name", ""),
                    "vat_number": invoice.get("VAT_code", ""),
                    "address_street": invoice.get("visit_street", ""),
                    "address_city": invoice.get("visit_city", ""),
                    "address_province": invoice.get("visit_state", ""),
                    "address_postal_code": invoice.get("visit_postalcode", ""),
                    "first_name": invoice.get("firstname", ""),
                    "last_name": invoice.get("surname", ""),
                    "ei_code": invoice.get("code", ""),
                    # "address_extra": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}"
                }

                invoice_payload = {
                    "data": {
                        "type": "invoice",
                        "due_date": due_date1.strftime("%Y-%m-%d"),
                        "entity": entity_data,
                        "language": {"code": "it"},
                        "currency": {"id": "EUR", "symbol": "€"},
                        "e_invoice": True,
                        "ei_data":{
                            "bank_beneficiary":"NK EVENTS SRL",
                            "bank_name":"IT76I0313801600000013394747",
                            "cig":"",
                            "cup":"",
                            "od_date":"2025-05-08",
                            "od_number":"",
                            "original_document_type":"",
                            "payment_method":"MP05",
                            "vat_kind":"I",
                            "invoice_date":"2025-05-08",
                            "invoice_number":""
                        },
                        "items_list": items_list,
                        "payments_list": payments_list,
                        "show_payment_method": True,
                        "payment_method": {
                            "name": "Bonifico bancario",
                            "is_default": False,
                            "details": [
                                {
                                    "title": "BANCA REALE",
                                    "description": "IT76I0313801600000013394747"
                                },
                                {
                                    "title": "Intestatario",
                                    "description": "NK EVENTS SRL"
                                },
                                {
                                    "title": "Bic/Swift",
                                    "description": "BRTOITTT"
                                }
                            ],
                            "bank_iban": "IT76I0313801600000013394747",
                            "bank_name": "IT76I0313801600000013394747",
                            "bank_beneficiary": "NK EVENTS SRL",
                            "ei_payment_method": "MP05",
                            "label": "Bonifico bancario - IT76I0313801600000013394747"
                        },
                        "options": {
                            "fix_payments": True
                        }
                    }
                }

                # print("✅ FIRST invoice payload:", invoice_payload)
                create_invoice(invoice_payload)

                # SAVE SECOND INVOICE DETAILS
                second_invoice_entry = {
                    "customer_id": invoice.get("customer_id", ""),
                    "project_id": project.get("id", ""),
                    "invoice_date": second_invoice_date.strftime("%Y-%m-%d"),
                    "due_date": second_due_date.strftime("%Y-%m-%d"),
                    "amount": int(round(total_price * 0.6)),
                    "items_list": items_list,
                    "entity": entity_data
                }
                save_second_invoice_data(second_invoice_entry)
                # print('second_invoice_entry: ', second_invoice_entry)
                process_second_invoices()

        elif billing_date == "Fattura Acconto 30 Alla Conferma":
            print('items_list5555555555555555555555555: ', items_list)
            items_list = [
                item for item in items_list
                if re.search(r'Numero preventivo \d{4}-', item['name'])
            ]
            print('items_list30000000000000000000000000000: ', items_list)

            if items_list:
                total_price = round(float(sum(item['net_price'] for item in items_list)), 2)
                print('total_price: ', total_price)

                start_date_obj = datetime.fromisoformat(project['usageperiod_start'])
                end_date_obj = datetime.fromisoformat(project['usageperiod_end'])

                invoice_date = dt.date.today()
                due_date = invoice_date + dt.timedelta(days=30)
                second_invoice_date = end_date_obj + dt.timedelta(days=1)
                second_due_date = second_invoice_date + dt.timedelta(days=30)

                first_invoice_amount = int(round(total_price * 0.3))
                aaa = calculate_due_dates(payment_term, invoice_date, end_date_obj)
                due_date = ''
                for d in aaa:
                    due_date = d['due_date']
                print('aaa555555555555555555555555551: ', due_date)
                year = due_date.year
                month = due_date.month
                last_day = monthrange(year, month)[1]  # Get the last day of the month

                # Construct full last date of the month (with time if needed)
                due_date1 = due_date.replace(day=last_day)
                print('due_date:', due_date)
                print('due_date1: ', due_date1)

                payments_list = [{
                    "id": -1,
                    "amount": first_invoice_amount,
                    "due_date": due_date1.strftime("%Y-%m-%d"),
                    "payment_terms": {"days": 30, "type": "standard"},
                    "status": "not_paid"
                }]

                entity_data = {
                    "country": "Italia",
                    "name": invoice.get("customer_name", ""),
                    "vat_number": invoice.get("VAT_code", ""),
                    "address_street": invoice.get("visit_street", ""),
                    "address_city": invoice.get("visit_city", ""),
                    "address_province": invoice.get("visit_state", ""),
                    "address_postal_code": invoice.get("visit_postalcode", ""),
                    "first_name": invoice.get("firstname", ""),
                    "last_name": invoice.get("surname", ""),
                    "ei_code": invoice.get("code", ""),
                    # "address_extra": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}"
                }

                invoice_payload = {
                    "data": {
                        "type": "invoice",
                        "due_date": due_date1.strftime("%Y-%m-%d"),
                        "entity": entity_data,
                        "language": {"code": "it"},
                        "currency": {"id": "EUR", "symbol": "€"},
                        "e_invoice": True,
                        "ei_data":{
                            "bank_beneficiary":"NK EVENTS SRL",
                            "bank_name":"IT76I0313801600000013394747",
                            "cig":"",
                            "cup":"",
                            "od_date":"2025-05-08",
                            "od_number":"",
                            "original_document_type":"",
                            "payment_method":"MP05",
                            "vat_kind":"I",
                            "invoice_date":"2025-05-08",
                            "invoice_number":""
                        },
                        "items_list": items_list,
                        "payments_list": payments_list,
                        "show_payment_method": True,
                        "payment_method": {
                            "name": "Bonifico bancario",
                            "is_default": False,
                            "details": [
                                {
                                    "title": "BANCA REALE",
                                    "description": "IT76I0313801600000013394747"
                                },
                                {
                                    "title": "Intestatario",
                                    "description": "NK EVENTS SRL"
                                },
                                {
                                    "title": "Bic/Swift",
                                    "description": "BRTOITTT"
                                }
                            ],
                            "bank_iban": "IT76I0313801600000013394747",
                            "bank_name": "IT76I0313801600000013394747",
                            "bank_beneficiary": "NK EVENTS SRL",
                            "ei_payment_method": "MP05",
                            "label": "Bonifico bancario - IT76I0313801600000013394747"
                        },
                        "options": {
                            "fix_payments": True
                        }
                    }
                }

                # print("✅ FIRST 30% invoice payload:", invoice_payload)
                create_invoice(invoice_payload)

                # SAVE SECOND INVOICE DETAILS
                second_invoice_entry = {
                    "customer_id": invoice.get("customer_id", ""),
                    "project_id": project.get("id", ""),
                    "invoice_date": second_invoice_date.strftime("%Y-%m-%d"),
                    "due_date": second_due_date.strftime("%Y-%m-%d"),
                    "amount": int(round(total_price * 0.7)),
                    "items_list": items_list,
                    "entity": entity_data
                }

                save_second_invoice_data(second_invoice_entry)
                # print('second_invoice_entry: ', second_invoice_entry)
                process_second_invoices()
        
        elif billing_date == "Fattura Acconto 50 Alla Conferma":
            # Match quotes like "XXXX-"
            print('items_list66666666666666666666666666666: ', items_list)
            items_list = [
                item for item in items_list
                if re.search(r'Numero preventivo \d{4}-', item['name'])
            ]
            print('items_list500000000000000000000000000000000000000000: ', items_list)
            if items_list:
                total_price = round(float(sum(item['net_price'] for item in items_list)), 2)
                print('total_price: ', total_price)

                # Parse project dates
                start_date_obj = datetime.fromisoformat(project['usageperiod_start'])
                end_date_obj = datetime.fromisoformat(project['usageperiod_end'])

                invoice_date = dt.date.today()
                due_date = invoice_date + dt.timedelta(days=30)
                second_invoice_date = end_date_obj + dt.timedelta(days=1)
                second_due_date = second_invoice_date + dt.timedelta(days=30)

                # FIRST INVOICE: 50%
                first_invoice_amount = int(round(total_price * 0.5))
                aaa = calculate_due_dates(payment_term, invoice_date, end_date_obj)
                due_date = ''
                for d in aaa:
                    due_date = d['due_date']
                print('aaa66666666666666666666666666666: ', due_date)
                year = due_date.year
                month = due_date.month
                last_day = monthrange(year, month)[1]  # Get the last day of the month

                # Construct full last date of the month (with time if needed)
                due_date1 = due_date.replace(day=last_day)
                print('due_date1: ', due_date1)

                payments_list = [{
                    "id": -1,
                    "amount": first_invoice_amount,
                    "due_date": due_date1.strftime("%Y-%m-%d"),
                    "payment_terms": {"days": 30, "type": "standard"},
                    "status": "not_paid"
                }]

                entity_data = {
                    "country": "Italia",
                    "name": invoice.get("customer_name", ""),
                    "vat_number": invoice.get("VAT_code", ""),
                    "address_street": invoice.get("visit_street", ""),
                    "address_city": invoice.get("visit_city", ""),
                    "address_province": invoice.get("visit_state", ""),
                    "address_postal_code": invoice.get("visit_postalcode", ""),
                    "first_name": invoice.get("firstname", ""),
                    "last_name": invoice.get("surname", ""),
                    "ei_code": invoice.get("code", ""),
                    # "address_extra": f"Condizioni di pagamento: {payment_term_mapping.get(payment_term, "")}"
                }

                invoice_payload = {
                    "data": {
                        "type": "invoice",
                        "due_date": due_date1.strftime("%Y-%m-%d"),
                        "entity": entity_data,
                        "language": {"code": "it"},
                        "currency": {"id": "EUR", "symbol": "€"},
                        "e_invoice": True,
                        "ei_data":{
                            "bank_beneficiary":"NK EVENTS SRL",
                            "bank_name":"IT76I0313801600000013394747",
                            "cig":"",
                            "cup":"",
                            "od_date":"2025-05-08",
                            "od_number":"",
                            "original_document_type":"",
                            "payment_method":"MP05",
                            "vat_kind":"I",
                            "invoice_date":"2025-05-08",
                            "invoice_number":""
                        },
                        "items_list": items_list,
                        "payments_list": payments_list,
                        "show_payment_method": True,
                        # "ei_code": 
                        "payment_method": {
                            "name": "Bonifico bancario",
                            "is_default": False,
                            "details": [
                                {
                                    "title": "BANCA REALE",
                                    "description": "IT76I0313801600000013394747"
                                },
                                {
                                    "title": "Intestatario",
                                    "description": "NK EVENTS SRL"
                                },
                                {
                                    "title": "Bic/Swift",
                                    "description": "BRTOITTT"
                                }
                            ],
                            "bank_iban": "IT76I0313801600000013394747",
                            "bank_name": "IT76I0313801600000013394747",
                            "bank_beneficiary": "NK EVENTS SRL",
                            "ei_payment_method": "MP05",
                            "label": "Bonifico bancario - IT76I0313801600000013394747"
                        },
                        "options": {
                            "fix_payments": True
                        }
                    }
                }

                # print("✅ FIRST 50% invoice payload:", invoice_payload)
                create_invoice(invoice_payload)

                # SAVE SECOND INVOICE DETAILS (for 50% after project end)
                second_invoice_entry = {
                    "customer_id": invoice.get("customer_id", ""),
                    "project_id": project.get("id", ""),
                    "invoice_date": second_invoice_date.strftime("%Y-%m-%d"),
                    "due_date": second_due_date.strftime("%Y-%m-%d"),
                    "amount": int(round(total_price * 0.5)),
                    "items_list": items_list,
                    "entity": entity_data
                }

                save_second_invoice_data(second_invoice_entry)
                # print('second_invoice_entry: ', second_invoice_entry)
                process_second_invoices()
        return    
# if __name__ == "__main__":
#     main()
