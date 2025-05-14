from rentman_customer import get_rentman_contacts
from fatture_customer import get_clients_list

def compare_names(rentman_api_key, fatture_api_key):
    """
    Compares names from Rentman and Fatture in Cloud APIs and returns the matching ones.

    :param rentman_api_key: API key for Rentman
    :param fatture_api_key: API key for Fatture in Cloud
    :return: List of matching names
    """
    
    rentman_contacts = get_rentman_contacts(rentman_api_key)
    # print('rentman_contacts: ', rentman_contacts)
    fatture_clients = get_clients_list(fatture_api_key)
    # print('fatture_clients: ', fatture_clients)


    rentman_names = {contact.get('name') for contact in rentman_contacts if contact.get('name')}
    fatture_names = {client.get('name') for client in fatture_clients if client.get('name')}

    # print('fatture_names: ', fatture_names)
    # print('rentman_names: ', rentman_names)
    matching_names = rentman_names.intersection(fatture_names)

    return list(matching_names)

  

# print("Matching Names:", matching_names)