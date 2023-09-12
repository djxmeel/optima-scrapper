import odoorpc
import json
import os
import base64

from util import Util
from data_merger import DataMerger

IF_IMPORT_PRODUCTS = True
IF_IMPORT_ACC = True
IF_IMPORT_PDFS = True
IF_IMPORT_IMGS = True
IF_IMPORT_ICONS = True

odoo_host = 'trialdb.odoo.com'
odoo_protocol = 'jsonrpc+ssl'
odoo_port = '443'

odoo_db = 'trialdb'
odoo_login = 'itprotrial@outlook.com'
odoo_pass = 'itprotrial'

PRODUCT_INFO_DIR = 'merged_data/VTAC_PRODUCT_INFO'
PRODUCT_PDF_DIRS = {'es': 'vtac_spain/VTAC_PRODUCT_PDF/',
                    'uk': 'vtac_uk/VTAC_PRODUCT_PDF/',
                    'ita': 'vtac_italia/VTAC_PRODUCT_PDF/'}

SEPARATE_IMPORT_FIELDS = ('imgs', 'icons', 'kit', 'accesorios', 'videos')


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


def import_products():
    file_list = get_all_files_in_directory(PRODUCT_INFO_DIR)

    for file_path in file_list:
        with open(file_path, "r") as file:
            products = json.load(file)

        product_model = odoo.env['product.template']

        for product in products:
            product_ids = odoo.env['product.template'].search([('x_sku', '=', product['SKU'])])

            temp_keys = list(product.keys())
            sku = product["SKU"]

            for key in temp_keys:
                if key in SEPARATE_IMPORT_FIELDS:
                    del product[key]
                    continue
                if key not in Util.NOT_TO_EXTRACT_FIELDS:
                    product[Util.format_field_odoo(key)] = product[key]
                    del product[key]

            if not product_ids:
                product_id = product_model.create(product)

                print(f'Created product {sku}')
            else:
                print(f'Product {sku} already exists in Odoo with id {product_ids[0]}')

        print(f'IMPORTED PRODUCTS OF FILE : {file.name}')


def import_accessories_kits():
    file_list = get_all_files_in_directory(PRODUCT_INFO_DIR)

    # Get the product template object
    product_model = odoo.env['product.template']
    acc_model = odoo.env['x_accesorios_producto_model']

    # TODO TEST check of existing records
    # Delete all accessory model records
    # acc_model.unlink(acc_model.search([]))

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
                main_product_id = product_model.search([('x_sku', '=', product['SKU'])])
                if len(main_product_id) > 0:
                    main_product_id = main_product_id[0]

                print(f'SKU : {product["SKU"]} Accesorios : {len(accessories_sku)}')

                for acc in accessories_sku:
                    existing_acc_ids = acc_model.search([('x_producto', '=', main_product_id), ('x_sku', '=', acc['sku'])])

                    if len(existing_acc_ids) > 0:
                        print(f'UPDATED ACCESORIO OF PRODUCT WITH SKU {product["SKU"]} ID {main_product_id}')
                        updated_record_id = acc_model.write(existing_acc_ids[0], {'x_cantidad': acc['cantidad']})
                    else:
                        new_record_data = {
                            'x_sku': acc['sku'],
                            'x_producto': main_product_id,
                            'x_cantidad': acc['cantidad']
                        }

                        new_record_id = acc_model.create(new_record_data)
                        print(f'CREATED ACCESORIO OF PRODUCT WITH SKU {product["SKU"]} ID {main_product_id}')

# TODO TEST PDF 1.ES 2.UK MISSING : A check for sku existence to decide from what dir where to get the PDF from
def import_pdfs():
    product_model = odoo.env['product.template']
    pdf_model = odoo.env['x_product_files_model']

    directory_list_es = get_nested_directories(PRODUCT_PDF_DIRS['es'])
    sku_list_es = [dirr.split('/')[2] for dirr in directory_list_es]

    directory_list_uk = get_nested_directories(PRODUCT_PDF_DIRS['uk'])
    sku_list_uk = [dirr.split('/')[2] for dirr in directory_list_uk]

    directory_list_ita = get_nested_directories(PRODUCT_PDF_DIRS['ita'])
    sku_list_ita = [dirr.split('/')[2] for dirr in directory_list_ita]

    # TODO TEST the check of existing pdfs then remove
    # Delete all pdf model records
    # records = pdf_model.search([])
    # pdf_model.unlink(records)

    counter = 0

    unique_skus = DataMerger.get_unique_skus_from_merged()

    for sku in unique_skus:
        product_ids = product_model.search([('x_sku', '=', sku)])

        if len(product_ids) > 0:
            counter += 1
            print(f'{sku} FOUND IN ODOO ({counter})')

            pdf_paths = []

            # Remove 'VS' prefix [2:]
            if sku[2:] in sku_list_es:
                pdf_paths = Util.get_all_files_in_directory(directory_list_es[sku_list_es.index(sku[2:])])
            elif sku[2:] in sku_list_uk:
                pdf_paths = Util.get_all_files_in_directory(directory_list_es[sku_list_uk.index(sku[2:])])
            elif sku[2:] in sku_list_ita:
                pdf_paths = Util.get_all_files_in_directory(directory_list_es[sku_list_ita.index(sku[2:])])

            for pdf_path in pdf_paths:
                with open(pdf_path, 'rb') as file:
                    pdf_binary_data = file.read()
                    encoded_pdf_data = base64.b64encode(pdf_binary_data).decode()

                pdf_name = Util.translate_from_to_spanish('detect' ,pdf_path.split('\\')[-1])
                pdf_name = f'{sku}_{pdf_name}'

                existing_pdfs = pdf_model.search([('x_name', '=', pdf_name)])

                if not existing_pdfs:
                    pdf_data = {
                        'x_name': pdf_name,
                        'x_producto_file': encoded_pdf_data,
                        'x_producto': product_ids[0]
                    }

                    pdf_id = pdf_model.create(pdf_data)
                    print(f'PDF {pdf_name} DOES NOT EXIST IN ODOO, CREATED WITH ID {pdf_id}')
                else:
                    print(f'PDF {pdf_name} ALREADY EXISTS IN ODOO')


def import_imgs():
    file_list = get_all_files_in_directory(PRODUCT_INFO_DIR)

    for file_path in file_list:
        with open(file_path, "r") as file:
            json_data = json.load(file)

        for product_data in json_data:
            if 'imgs' in product_data:
                print(f'{product_data["SKU"]} imgs: {len(product_data["imgs"])}')

                # Search for the product template with the given sku
                product_ids = odoo.env['product.template'].search([('x_sku', '=', product_data['SKU'])])

                if product_ids:
                    print('PRODUCT FOUND IN ODOO')
                    # write/overwrite the image to the product
                    if len(product_data['imgs']) > 0:
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
            product_ids = odoo.env['product.template'].search([('x_sku', '=', product['SKU'])])

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
