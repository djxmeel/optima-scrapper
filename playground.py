import json
import os

import odoorpc

from utils.data_merger import DataMerger

odoo_host = 'trialdb-final.odoo.com'
odoo_protocol = 'jsonrpc+ssl'
odoo_port = '443'

odoo_db = 'trialdb-final'
odoo_login = 'itprotrial@outlook.com'
odoo_pass = 'itprotrial'

odoo = odoorpc.ODOO(odoo_host, protocol=odoo_protocol, port=odoo_port)
# Authenticate with your credentials
odoo.login(odoo_db, odoo_login, odoo_pass)

product_model = odoo.env['product.template']


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

            print(f"{i}/{len(product_ids)} NEW NAME : {name}")

    print(f"Updated {len(product_ids)} products.")

