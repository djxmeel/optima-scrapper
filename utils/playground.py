import json
import os
import base64
from PIL import Image
from io import BytesIO

import odoorpc

from scrapers.scraper_vtac_es import ScraperVtacSpain
from scrapers.scraper_vtac_ita import ScraperVtacItalia
from scrapers.scraper_vtac_uk import ScraperVtacUk
from utils.data_merger import DataMerger
from utils.util import Util


def login_odoo():
    odoo_host = 'trialdb-final.odoo.com'
    odoo_protocol = 'jsonrpc+ssl'
    odoo_port = '443'

    odoo_db = 'trialdb-final'
    odoo_login = 'itprotrial@outlook.com'
    odoo_pass = 'itprotrial'

    odoo = odoorpc.ODOO(odoo_host, protocol=odoo_protocol, port=odoo_port)
    # Authenticate with your credentials
    odoo.login(odoo_db, odoo_login, odoo_pass)

    return odoo


odoo = login_odoo()

product_model = odoo.env['product.template']
product_attributes_model = odoo.env['product.attribute']


def ecommerce_filter_visibility_modifier(is_visible):
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


def process_files(directory, old_key, new_key):
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


def process_names_to_ref(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)

            with open(file_path, 'r') as f:
                print(f"OPENING {file_path}")
                data = json.load(f)

            # Check if the old key exists and rename it
            for product in data:
                if 'name' in product:
                    product['name'] = f'[{product["default_code"]}] {product["name"].split("] ")[1]}'
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

def field_update():
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
    categs = list(Util.load_json_data('data/vtac_italia/LINKS/PRODUCT_LINKS_CATEGORIES.json').values())
    categs += list(Util.load_json_data('data/vtac_uk/LINKS/PRODUCT_LINKS_CATEGORIES.json').values())

    distinct_categs = set()

    for categ_list in categs:
        for categ in categ_list:
            distinct_categs.add(categ)

    empty_translation_dict = {}

    for categ in sorted(list(distinct_categs)):
        empty_translation_dict[categ] = ''

    return empty_translation_dict


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
