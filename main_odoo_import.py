import time
import odoorpc
import json
import os
from googletrans import Translator
import base64


IF_IMPORT_PRODUCTS = True
IF_IMPORT_ACC = True
IF_IMPORT_PDFS = True
IF_IMPORT_IMGS = True
IF_IMPORT_ICONS = True

odoo_host = 'optest.odoo.com'
odoo_protocol = 'jsonrpc+ssl'
odoo_port = '443'

odoo_db = 'optest'
odoo_login = 'djamelnadour15@gmail.com'
odoo_pass = 'black20-00'

PRODUCT_INFO_LITE_DIR = 'vtac_italia/VTAC_PRODUCT_INFO_LITE/'
PRODUCT_INFO_DIR = 'vtac_italia/VTAC_PRODUCT_INFO/'
PRODUCT_PDF_DIR = 'vtac_italia/VTAC_PRODUCT_PDF/'


odoo = odoorpc.ODOO(odoo_host, protocol=odoo_protocol, port=odoo_port)

# Authenticate with your credentials
odoo.login(odoo_db, odoo_login, odoo_pass)


def get_all_files_in_directory(directory_path):
    all_files = []
    for root, dirs, files in os.walk(directory_path):
        for f in files:
            path = os.path.join(root, f)
            all_files.append(path)
    return all_files


def get_nested_directories(path):
    directories = []
    for root, dirs, _ in os.walk(path):
        for name in dirs:
            directories.append(os.path.join(root, name))
    return directories


def translate_italian_to_spanish(text):
    """
    Translates Italian text to Spanish using Google Translate.

    Parameters:
    text (str): The text in Italian.

    Returns:
    str: The translated text in Spanish.
    """
    try:
        translator = Translator()

        detected_language = translator.detect(text).lang

        if detected_language == 'it':
            translation = translator.translate(text, src=detected_language, dest='es')
            return translation.text
    except TimeoutError:
        print('TIMED OUT')
        translate_italian_to_spanish(text)

    return text


def import_products():
    file_list = get_all_files_in_directory(PRODUCT_INFO_LITE_DIR)

    for file_path in file_list:
        with open(file_path, "r") as file:
            products = json.load(file)

        product_model = odoo.env['product.template']

        for product in products:
            product_ids = odoo.env['product.template'].search([('x_SKU', '=', product['x_SKU'])])

            if not product_ids:
                product_id = product_model.create(product)

                print(f'Created product {product["x_SKU"]}')
            else:
                print(f'Product {product["x_SKU"]} already exists in Odoo with id {product_ids[0]}')

        print(f'IMPORTED PRODUCTS OF FILE : {file.name}')


def import_accessories_kits():

    file_list = get_all_files_in_directory(PRODUCT_INFO_DIR)

    # Get the product template object
    product_model = odoo.env['product.template']
    acc_model = odoo.env['x_accesorios_producto_model']

    # TODO CHANGE to a check of existing records
    # Delete all accessory model records
    acc_model.unlink(acc_model.search([]))

    for file_path in file_list:
        with open(file_path, "r") as file:
            print(file.name)
            json_data = json.load(file)

        # Iterate over the products
        for index, product in enumerate(json_data):
            accessories_sku = []

            if 'kit' in product and len(product['kit']) > 0:
                for kit in product['kit']:
                    accessories_sku.append(kit)

            if 'accesorios' in product and len(product['accesorios']) > 0:
                for acc in product['accesorios']:
                    accessories_sku.append(acc)

            if len(accessories_sku) > 0:
                # Search for the product template with the given name
                main_product_id = product_model.search([('x_SKU', '=', product['SKU'])])[0]

                print(f'SKU : {product["SKU"]} Accesorios : {len(accessories_sku)}')

                for acc in accessories_sku:
                    new_record_data = {
                        'x_sku': acc['sku'],  # Any other fields you want to set
                        'x_producto': main_product_id,  # The ID of the product you want to reference
                        'x_cantidad': acc['cantidad']
                    }
                    new_record_id = acc_model.create(new_record_data)

            print(f"#{index + 1} ADDED {len(accessories_sku)} ACCESSORIES TO PRODUCT WITH SKU {product['SKU']}")


def import_pdfs():
    product_model = odoo.env['product.template']
    pdf_model = odoo.env['x_product_files_model']

    directory_list = get_nested_directories(PRODUCT_PDF_DIR)
    counter = 0

    records = pdf_model.search([])

    # TODO CHANGE a check of existing pdfs
    # Delete all pdf model records
    pdf_model.unlink(records)

    for directory in directory_list:
        sku = f"VS{directory.split('/')[1]}".upper()

        pdf_paths = get_all_files_in_directory(directory)
        product_ids = product_model.search([('x_SKU', '=', sku)])

        if len(product_ids) > 0:
            counter += 1
            print(f'{sku} FOUND IN ODOO ({counter}/4715)')
            for pdf_path in pdf_paths:

                with open(pdf_path, 'rb') as file:
                    pdf_binary_data = file.read()
                    encoded_pdf_data = base64.b64encode(pdf_binary_data).decode()

                pdf_name = translate_italian_to_spanish(pdf_path.split('\\')[-1])
                pdf_name = f'{sku}_{pdf_name}'
                time.sleep(1)

                existing_pdfs = pdf_model.search([('x_name', '=', pdf_name)])

                if not existing_pdfs:
                    print(pdf_name)
                    pdf_data = {
                        'x_name': pdf_name,
                        'x_producto_file': encoded_pdf_data,
                        'x_producto': product_ids[0],
                    }

                    pdf_id = pdf_model.create(pdf_data)


def import_imgs():
    file_list = get_all_files_in_directory(PRODUCT_INFO_DIR)

    for file_path in file_list:
        with open(file_path, "r") as file:
            json_data = json.load(file)

        for product_data in json_data:
            if 'imgs' in product_data:
                print(f'{product_data["SKU"]} imgs: {len(product_data["imgs"])}')

                # Search for the product template with the given sku
                product_ids = odoo.env['product.template'].search([('x_SKU', '=', product_data['SKU'])])

                if product_ids:
                    print('PRODUCT FOUND IN ODOO')
                    # write/overwrite the image to the product
                    odoo.env['product.template'].write([product_ids[0]], {'image_1920': product_data['imgs'][0]['img64']})

                    image_ids = odoo.env['product.image'].search([('product_tmpl_id', '=', product_ids[0])])

                    # Product existing images
                    images = odoo.env['product.image'].browse(image_ids)

                    images = [image.image_1920 for image in images]

                    # Iterate over the products
                    for extra_img in product_data['imgs'][1:]:
                        if not images.__contains__(extra_img['img64']):
                            new_image = {
                                'name': f'{product_ids[0]}_{product_data["imgs"].index(extra_img)}',
                                # Replace with your image name
                                'image_1920': extra_img['img64'],
                                'product_tmpl_id': product_ids[0]
                            }

                            # Create the new product.image record
                            odoo.env['product.image'].create(new_image)
                        else:
                            print('Image already exists')
                else:
                    print('PRODUCT NOT FOUND IN ODOO')

            else:
                print(f'{product_data["SKU"]} HAS NO IMAGES!')


def import_icons():
    file_list = get_all_files_in_directory(PRODUCT_INFO_DIR)

    for file_path in file_list:
        with open(file_path, "r") as file:
            json_data = json.load(file)

    for product in json_data:
        if 'icons' in product:
            print(f'{product["SKU"]} icons: {len(product["icons"])}')

            # Search for the product template with the given sku
            product_ids = odoo.env['product.template'].search([('x_SKU', '=', product['SKU'])])

            if product_ids:
                print('PRODUCT FOUND IN ODOO')

                image_ids = odoo.env['product.image'].search([('product_tmpl_id', '=', product_ids[0])])

                # Product existing icons
                images = odoo.env['product.image'].browse(image_ids)

                images = [image.image_1920 for image in images]

                # Iterate over the products
                for icon in product['icons']:
                    if not images.__contains__(icon):
                        new_image = {
                            'name': f'{product_ids[0]}_{product["icons"].index(icon)}',  # Replace with your image name
                            'image_1920': icon,
                            'product_tmpl_id': product_ids[0]
                        }
                        # Create the new product.image record
                        odoo.env['product.image'].create(new_image)
                    else:
                        print('Icon already exists')
            else:
                print('PRODUCT NOT FOUND IN ODOO')

        else:
            print(f'{product["SKU"]} HAS NO ICONS!')


if IF_IMPORT_PRODUCTS:
    print(f'BEGINNING PRODUCTS IMPORT')
    import_products()
    print(f'FINISHED PRODUCTS IMPORT')


if IF_IMPORT_ACC:
    print(f'BEGINNING ACCESSORIES/KITS IMPORT')
    import_accessories_kits()
    print(f'FINISHED ACCESSORIES/KITS IMPORT')


if IF_IMPORT_PDFS:
    print(f'BEGINNING PDFS IMPORT')
    import_pdfs()
    print(f'FINISHED PDFS IMPORT')


if IF_IMPORT_IMGS:
    print(f'BEGINNING IMGS IMPORT')
    import_imgs()
    print(f'FINISHED IMGS IMPORT')


if IF_IMPORT_ICONS:
    print(f'BEGINNING ICONS IMPORT')
    import_icons()
    print(f'FINISHED ICONS IMPORT')
