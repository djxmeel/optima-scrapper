import json
import os
import base64
from PIL import Image
from io import BytesIO
import pandas as pd

import odoorpc

from utils.data_merger import DataMerger
from utils.util import Util


def login_odoo():
    #odoo_host = 'trialdb-final2.odoo.com'
    odoo_host = 'optimaluz.soluntec.net'
    odoo_protocol = 'jsonrpc+ssl'
    odoo_port = '443'

    #odoo_db = 'trialdb-final2'
    #odoo_login = 'itprotrial@outlook.com'
    #odoo_pass = 'itprotrial'

    odoo_db = 'Pruebas'
    odoo_login = 'productos@optimaluz.com'
    odoo_pass = '96c04503fc98aa4ffd90a9cf72ceb2d90d709b01'

    odoo = odoorpc.ODOO(odoo_host, protocol=odoo_protocol, port=odoo_port)
    # Authenticate with your credentials
    odoo.login(odoo_db, odoo_login, odoo_pass)

    return odoo

def change_internal_ref_odoo():
    odoo = login_odoo()

    product_model = odoo.env['product.template']

    # Fetch records in batches to avoid RPCerror
    batch_size = 200
    offset = 0
    products = []

    while True:
        product_ids = product_model.search([], offset=offset, limit=batch_size)
        if not product_ids:  # Exit the loop when no more records are found
            break

        products.extend(product_model.browse(product_ids))
        print(len(products))

        offset += batch_size

    for product in products:
        product_model.write(product.id, {'default_code': product.x_sku})


def ecommerce_filter_visibility_modifier(is_visible):
    odoo = login_odoo()
    product_attributes_model = odoo.env['product.attribute']

    attributes_ids = product_attributes_model.search([])

    product_attributes_model.write(attributes_ids, {'visibility': is_visible})


def rename_key_in_json_file(file_path, old_key, new_key):
    """
    Reads the JSON file, renames a specified key, and writes back the modified content.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Check if the old key exists and rename it
    for product in data:
        if old_key in product:
            product[new_key] = product.pop(old_key)

    with open(file_path, 'w') as f:
        json.dump(data, f)


def rename_key_in_directory_jsons(directory, old_key, new_key):
    """
    Processes all JSON files in the specified directory and renames the old_key to new_key.
    """
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            rename_key_in_json_file(file_path, old_key, new_key)
            print(f"Processed {file_path}")


def process_sku_to_ref(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)

            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            # Check if the old key exists and rename it
            for product in data:
                if 'Sku' in product:
                    try:
                        if not product["Sku"].__contains__("VS"):
                            new_sku = int(product["Sku"])
                        else:
                            new_sku = int(product["Sku"][2:])
                    except ValueError:
                        product['default_code'] = f'VS{product["Sku"]}'
                        continue

                    product['default_code'] = f'VS{new_sku * 2}'
                    product['Sku'] = str(new_sku)
            with open(file_path, 'w') as f:
                json.dump(data, f)

            print(f"Processed {file_path}")


def process_ref_to_sku(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)

            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            # Check if the old key exists and rename it
            for product in data:
                if 'Sku' in product:
                    product['default_code'] = product['Sku']
                    del product['Sku']
                else:
                    product['default_code'] = str(int(int(product["default_code"][2:]) / 2))
            with open(file_path, 'w') as f:
                json.dump(data, f)

            print(f"Processed {file_path}")


def process_names_to_ref__clean_bad_skus(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)

            bad_sku_products = []

            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            # Check if the old key exists and rename it
            for product in data:
                if 'name' in product:
                    try:
                        product['name'] = f'[VS{int(product["default_code"]) * 2}] {product["name"].split("] ")[1]}'
                    except ValueError:
                        bad_sku_products.append(product)
                        print("REMOVING PRODUCT W/ BAD SKU: " + product['default_code'])
                        continue

            for product in bad_sku_products:
                data.remove(product)

            with open(file_path, 'w') as f:
                json.dump(data, f)

            print(f"Processed {file_path}")


def process_sku_to_ref_acc(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)

            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            # Check if the old key exists and rename it
            for product in data:
                if 'accesorios' in product:
                    for acc in product['accesorios']:
                        new_sku = int(acc["sku"][2:])

                        acc['default_code'] = f'VS{new_sku * 2}'
                        del acc['sku']

            with open(file_path, 'w') as f:
                json.dump(data, f)

            print(f"Processed {file_path}")


def process_ref_to_sku_acc(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)

            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            # Check if the old key exists and rename it
            for product in data:
                if 'accesorios' in product:
                    for acc in product['accesorios']:
                        if acc["default_code"].__contains__("VS"):
                            acc['default_code'] = str(int(int(acc["default_code"][2:]) / 2))
            with open(file_path, 'w') as f:
                json.dump(data, f)

            print(f"Processed {file_path}")


def field_update():
    odoo = login_odoo()

    product_model = odoo.env['product.template']
    product_attributes_model = odoo.env['product.attribute']

    product_ids = product_model.search([])

    for i, product_id in enumerate(product_ids):
        product_obj = product_model.browse(product_id)
        sku = product_obj.x_sku
        name = product_obj.name

        if sku:
            if sku[:2] == 'VS':
                sku = sku[2:]

            ref = f'VS{int(sku) * 2}'

            index = str(name).index(']')
            name = str(name).replace(name[:index + 1], f'[{ref}]')

            product_model.write(product_id, {
                'x_sku': sku,
                'default_code': ref,
                'name': name
            })

            print(f"{i}/{len(product_ids)} NEW NAME: {name}")

    print(f"Updated {len(product_ids)} products.")

def get_distinct_categs():
    categs = list(Util.load_json('data/vtac_italia/LINKS/PRODUCT_LINKS_CATEGORIES.json').values())
    categs += list(Util.load_json('data/vtac_uk/LINKS/PRODUCT_LINKS_CATEGORIES.json').values())

    distinct_categs = set()

    for categ_list in categs:
        for categ in categ_list:
            distinct_categs.add(categ)

    empty_translation_dict = {}

    for categ in sorted(list(distinct_categs)):
        empty_translation_dict[categ] = ''

    return empty_translation_dict


def generate_all_products_info_json(directory):
    """Generates a JSON file with all the products info from the specified directory."""
    products_info = []

    for file_path in Util.get_all_files_in_directory(directory):
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            products_info.extend(data)

    Util.dump_to_json(products_info, 'data/common/PRODUCT_INFO_ALL.json')


def convert_xlsx_to_json(excel_file_path, json_file_path):
    # Load the XLSX file into a pandas DataFrame
    df = pd.read_excel(excel_file_path)

    # Convert the DataFrame to JSON
    json_data = df.to_json(orient='records', date_format='iso')

    # If you want to write the JSON data to a file, you could do so like this:
    with open(json_file_path, 'w') as json_file:
        json_file.write(json_data)

    return json_data


def decode_and_save_b64_image(b64_string, output_folder, image_name):
    """Decode base64 string to image and save it"""
    image_data = base64.b64decode(b64_string)
    image = Image.open(BytesIO(image_data))
    image.save(os.path.join(output_folder, image_name))


def get_distinct_b64_imgs_from_json(dir_path, output_folder, field):
    """Process a JSON file with base64 encoded images and save DISTINCT images to a folder"""
    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    files_paths = Util.get_all_files_in_directory(dir_path)
    b64_strings = []

    for file_path in files_paths:
        # Load the JSON data
        with open(file_path, 'r') as f:
            products_media = json.load(f)

        for product in products_media:
            if field not in product:
                continue

            # Get distinct base64 strings
            b64_strings.extend(product[field])
            print(len(b64_strings))

    distinct_b64_strings = list(set(b64_strings))
    print(len(distinct_b64_strings))

    # Decode and save each distinct image
    for index, b64_string in enumerate(distinct_b64_strings, 1):
        image_name = f'image_{index}.png'
        decode_and_save_b64_image(b64_string, output_folder, image_name)



#get_distinct_b64_imgs_from_json('data/vtac_merged/PRODUCT_MEDIA', 'data/unique_icons', 'icons')
# Util.dump_to_json(get_distinct_categs(), Util.PUBLIC_CATEGORIES_TRANSLATION_PATH)

#ecommerce_filter_visibility_modifier('hidden')

#convert_xlsx_to_json('data/common/VTAC_ES_PUBLIC_CATEGORIES.xlsx', 'data/common/PUBLIC_CATEGORIES.json')


#process_ref_to_sku(DataMerger.MERGED_PRODUCT_INFO_DIR_PATH)
#process_ref_to_sku(DataMerger.MERGED_PRODUCT_MEDIA_DIR_PATH)

#process_ref_to_sku_acc(DataMerger.MERGED_PRODUCT_INFO_DIR_PATH)
#change_internal_ref_odoo()

generate_all_products_info_json(DataMerger.MERGED_PRODUCT_INFO_DIR_PATH)

