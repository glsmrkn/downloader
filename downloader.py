import os

import requests
import json
import datetime

try:
  from IPython.display import clear_output
except:
    clear_output = None


search_url = 'https://webgate.ec.europa.eu/rasff-window/backend/public/notification/search/consolidated/'
notification_types_url = 'https://webgate.ec.europa.eu/rasff-window/backend/public/productType/list/'
product_categories_url = 'https://webgate.ec.europa.eu/rasff-window/backend/public/productCategory/list/'
hazard_categories_url = 'https://webgate.ec.europa.eu/rasff-window/backend/public/hazardCategory/list/'
risk_decisions_url = 'https://webgate.ec.europa.eu/rasff-window/backend/public/riskDecision/list/'

csv_delimiter = '|'

def get_params(
        page,
        start_date,
        end_date,
        notification_type_ids,
        product_category_ids,
        hazard_category_ids,
        risk_decision_ids):

    params = []
    if start_date:
        params.append('"ecValidDateFrom":"' + start_date + ' 00:00:00"')
    if end_date:
        params.append('"ecValidDateTo":"' + end_date + ' 00:00:00"')
    if notification_type_ids:
        params.append('"notificationType":' + str(notification_type_ids))
    if product_category_ids:
        params.append('"productCategory":' + str(product_category_ids))
    if hazard_category_ids:
        params.append('"hazardCategory":' + str(hazard_category_ids))
    if risk_decision_ids:
        params.append('"riskDecision":' + str(risk_decision_ids))

    joined_params = ','.join(params)
    params_to_request = ',' + joined_params if joined_params else ''
    params_raw = '{"parameters":{"pageNumber":' + str(page) + ',"itemsPerPage":25}' + params_to_request + '}'
    return json.loads(params_raw)


def fetch_details(
        start_date,
        end_date,
        notification_type_ids,
        product_category_ids,
        hazard_category_ids,
        risk_decision_ids):

    initial_params = get_params(
        1,
        start_date,
        end_date,
        notification_type_ids,
        product_category_ids,
        hazard_category_ids,
        risk_decision_ids
    )

    resp = requests.post(url=search_url, json=initial_params)
    data = resp.json()

    total_pages = data['totalPages']
    total_elements = data['totalElements']
    processed_element_count = 1

    result = 'Notifying' + csv_delimiter + \
             'Origin' + csv_delimiter + \
             'Distribution' + csv_delimiter + \
             'Subject' + csv_delimiter + \
             'Hazards' + csv_delimiter + \
             'Hazard Categories' + csv_delimiter + \
             'Validation Date\n'
    for page in range(1, total_pages + 1):
        params = get_params(
            page,
            start_date,
            end_date,
            notification_type_ids,
            product_category_ids,
            hazard_category_ids,
            risk_decision_ids
        )

        try:
            resp = requests.post(url=search_url, json=params, timeout=15)
            data = resp.json()
            element_ids = map(lambda x: x['notifId'], data['notifications'])
        except Exception as e:
            print('Error while fetching page details: ' + str(page) + '. Error: ' + str(e))
            continue

        if not element_ids:
            print('Error! Result is empty for page: ' + str(page))
            continue

        for nid in element_ids:
            print('Processing: ' + str(nid) + '\t(Item: ' + str(processed_element_count) + "/" + str(
                total_elements) + ' Page: ' + str(page) + '/' + str(total_pages) + ')')
            id_url = 'https://webgate.ec.europa.eu/rasff-window/backend/public/notification/view/id/' + str(nid) + '/'
            processed_element_count += 1

            try:
                details_resp = requests.get(url=id_url, timeout=15)
                details = details_resp.json()

                organization_flags = details['organizationFlags']
                raw_notifying_arr = list(map(lambda x: x['organization']['description'], filter(lambda d: 'notifying' in d, organization_flags)))
                notifying = ','.join(raw_notifying_arr).strip() if raw_notifying_arr else '-'

                raw_origin_arr = list(map(lambda x: x['organization']['description'], filter(lambda d: 'origin' in d, organization_flags)))
                origin = ','.join(raw_origin_arr).strip() if raw_origin_arr else '-'

                raw_distribution_arr = list(map(lambda x: x['organization']['description'], filter(lambda d: 'distribution' in d, organization_flags)))
                distribution = ','.join(raw_distribution_arr).strip() if raw_distribution_arr else '-'

                raw_subject = details['subject']
                subject = str(raw_subject).strip() if raw_subject else '-'

                raw_hazards_arr = list(map(lambda x: x['name'], details['product']['hazards']))
                hazards = ','.join(raw_hazards_arr).strip() if raw_hazards_arr else '-'

                raw_hazard_categories_arr = list(map(lambda x: x['hazardCategory']['description'], details['product']['hazards']))
                hazard_categories = ','.join(raw_hazard_categories_arr).strip() if raw_hazard_categories_arr else '-'

                raw_validation_date = details['ecValidationDate']
                validation_date = str(raw_validation_date).strip() if raw_validation_date else '-'

                result += csv_delimiter.join([notifying, origin, distribution, subject, hazards, hazard_categories, validation_date]) + '\n'

            except Exception as e:
                print('Unable to process: ' + str(nid) + '. Error: ' + str(e))

    return result


def fetch_and_select_ids(url, selector, name):
    types_resp = requests.get(url=url, timeout=15)
    types_json = types_resp.json()
    all_types = types_json[selector]

    if clear_output:
        clear_output()

    print('-------------\n' + name + ':')
    for index in range(0, len(all_types)):
        print('[' + str(index + 1) + '] = ' + all_types[index]['description'])

    raw_indices = input('Select single or (comma separated multiple) values for ' + name + ' (e.g. 1 OR 1,4,7). Leave empty to select all: ')
    if not raw_indices:
        return []

    split_indices = raw_indices.strip().split(',')
    selected_indices = list(map(int, split_indices))
    if not selected_indices:
        return []

    return [all_types[index-1]['id'] for index in selected_indices]


start_date = input("Start date (e.g. 20-01-2020): ")
end_date = input("End date (e.g. 20-01-2020): ")
notification_type_ids = fetch_and_select_ids(notification_types_url, 'notificationTypes', 'Notification Types')
product_category_ids = fetch_and_select_ids(product_categories_url, 'productCategories', 'Product Categories')
hazard_category_ids = fetch_and_select_ids(hazard_categories_url, 'hazardCategories', 'Hazard Categories')
risk_decision_ids = fetch_and_select_ids(risk_decisions_url, 'riskDecisions', 'Risk Decisions')

if clear_output:
    clear_output()

details_list = fetch_details(
    start_date,
    end_date,
    notification_type_ids,
    product_category_ids,
    hazard_category_ids,
    risk_decision_ids
)

if clear_output:
    clear_output()

try:
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    output_path = os.path.join(__location__, "rasff_" + str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))) + ".csv"
    with open(output_path, "w") as csv_file:
        csv_file.write(details_list)

    print("File created at: " + output_path)
    input("Press enter to exit...")
except:
    print("---------\n\nResults:\n\n" + details_list)
