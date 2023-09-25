import copy
from urllib.error import HTTPError

import odoorpc
import json
import base64

from odoorpc.error import RPCError

from utils.util import Util
from utils.data_merger import DataMerger


class OdooImport:
    logger = None

    odoo_host = 'trialdb2.odoo.com'
    odoo_protocol = 'jsonrpc+ssl'
    odoo_port = '443'

    odoo_db = 'trialdb2'
    odoo_login = 'itprotrial@outlook.com'
    odoo_pass = 'itprotrial'

    odoo = odoorpc.ODOO(odoo_host, protocol=odoo_protocol, port=odoo_port)

    # Authenticate with your credentials
    odoo.login(odoo_db, odoo_login, odoo_pass)

    ATTRIBUTE_MODEL = odoo.env['product.attribute']
    ATTRIBUTE_VALUE_MODEL = odoo.env['product.attribute.value']
    ATTRIBUTE_LINE_MODEL = odoo.env['product.template.attribute.line']

    MEDIA_MODEL = odoo.env['product.image']
    PRODUCT_MODEL = odoo.env['product.template']

    PRODUCT_INFO_DIR = 'data/vtac_merged/PRODUCT_INFO'
    PRODUCT_PDF_DIRS = {'es': 'vtac_es/PRODUCT_PDF/',
                        'uk': 'vtac_uk/PRODUCT_PDF/',
                        'ita': 'vtac_ita/PRODUCT_PDF/'}

    # Fields not to create as attributes in ODOO
    NOT_ATTR_FIELDS = ('accesorios', 'videos', 'icons', 'imgs', 'EAN', 'Código de familia', 'url')

    @classmethod
    def create_attribute(cls, name, value):
        attribute_vals = {
            'name': name,
            'create_variant': 'no_variant',  # Variants are created "always", "no_variant", or "dynamic"
        }

        attribute_ids = cls.ATTRIBUTE_MODEL.search([('name', '=', name)])

        if attribute_ids:
            attribute_id = attribute_ids[0]
        else:
            attribute_id = cls.ATTRIBUTE_MODEL.create(attribute_vals)
            cls.logger.info(f'CREATED NEW ATTRIBUTE : {name}')

        # Skip empty values
        if str(value).strip() == '':
            return

        # Create attribute values
        attribute_value_vals = {
            'name': value,
            'attribute_id': attribute_id
        }
        try:
            cls.ATTRIBUTE_VALUE_MODEL.create(attribute_value_vals)
        except RPCError:
            pass

    @classmethod
    def assign_attribute_values(cls, product_id, product, attributes):
        for attribute in attributes:
            attribute_id = cls.ATTRIBUTE_MODEL.search([('name', '=', attribute)])[0]
            attribute_value_ids = cls.ATTRIBUTE_VALUE_MODEL.search([('name', '=', product[attribute]), ('attribute_id', '=', attribute_id)])

            if attribute_value_ids:
                existing_lines = cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id), ('value_ids', '=', attribute_value_ids)])

                # Skip if the attribute line already exists with the same value
                if existing_lines:
                    # TODO remove
                    print(f"Skipping {attribute} for product {product['sku']} as it already exists with the same value")
                    continue
                # TODO TEST attr update & creation
                # Delete existing lines with the same attribute but different value
                old_lines = cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)])
                if old_lines:
                    # TODO remove
                    print(f"Unlinking {attribute} for product {product['sku']} to update it with the new value {product[attribute]}")
                    cls.ATTRIBUTE_LINE_MODEL.unlink(old_lines)

                line_vals = {
                    'product_tmpl_id': product_id,
                    'attribute_id': attribute_id,
                    'value_ids': [(6, 0, attribute_value_ids)]
                }
                try:
                    cls.ATTRIBUTE_LINE_MODEL.create(line_vals)
                except RPCError:
                    pass

    @classmethod
    def import_products(cls):
        file_list = Util.get_all_files_in_directory(cls.PRODUCT_INFO_DIR)
        for file_path in file_list:
            with open(file_path, "r") as file:
                products = json.load(file)

            product_model = cls.PRODUCT_MODEL

            for product in products:
                product_ids = cls.PRODUCT_MODEL.search([('x_sku', '=', product['sku'])])

                created_attrs = []
                temp_keys = list(product.keys())
                product_copy = copy.deepcopy(product)

                sku = product["sku"]

                for key in temp_keys:
                    if key not in Util.ODOO_SUPPORTED_FIELDS:
                        if key not in cls.NOT_ATTR_FIELDS:
                            cls.create_attribute(key, product[key])
                            created_attrs.append(key)
                        if key not in Util.ODOO_CUSTOM_FIELDS:
                            del product[key]
                        else:
                            product[Util.format_field_odoo(key)] = product[key]
                            del product[key]

                if not product_ids:
                    product_id = product_model.create(product)
                    cls.logger.info(f'Created product {sku}')
                else:
                    product_id = product_ids[0]
                    cls.logger.info(f'Product {sku} already exists in Odoo with id {product_ids[0]}')

                cls.assign_attribute_values(product_id, product_copy, created_attrs)

            cls.logger.info(f'IMPORTED PRODUCTS OF FILE : {file.name}')

    @classmethod
    def import_accessories(cls):
        file_list = Util.get_all_files_in_directory(cls.PRODUCT_INFO_DIR)

        # Get the product template object
        acc_model = cls.odoo.env['x_accesorios_producto_model']

        # Delete all accessory model records
        # acc_model.unlink(acc_model.search([]))

        for file_path in file_list:
            with open(file_path, "r") as file:
                json_data = json.load(file)

            # Iterate over the products
            for index, product in enumerate(json_data):
                accessories_sku = []

                if 'accesorios' in product and product['accesorios']:
                    for acc in product['accesorios']:
                        accessories_sku.append(acc)

                if accessories_sku:
                    # Search for the product template with the given name
                    main_product_id = cls.PRODUCT_MODEL.search([('x_sku', '=', product['sku'])])
                    if main_product_id:
                        main_product_id = main_product_id[0]
                        cls.logger.info(f'SKU : {product["sku"]} Accesorios : {len(accessories_sku)}')
                    else:
                        continue

                    for acc in accessories_sku:
                        existing_acc_ids = acc_model.search([('x_producto', '=', main_product_id), ('x_sku', '=', acc['sku'])])

                        if existing_acc_ids:
                            cls.logger.info(f'UPDATED ACCESORIO OF PRODUCT WITH SKU {product["sku"]} ID {main_product_id}')
                            updated_record_id = acc_model.write(existing_acc_ids[0], {'x_cantidad': acc['cantidad']})
                        else:
                            new_record_data = {
                                'x_sku': acc['sku'],
                                'x_producto': main_product_id,
                                'x_cantidad': acc['cantidad']
                            }

                            new_record_id = acc_model.create(new_record_data)
                            cls.logger.info(f'CREATED ACCESORIO OF PRODUCT WITH SKU {product["sku"]} ID {main_product_id}')


    # TODO search for skus in ODOO and use them to browse through dirs for potential DLs
    @classmethod
    def import_pdfs(cls):
        product_model = cls.PRODUCT_MODEL
        attachments_model = cls.odoo.env['ir.attachment']

        directory_list_es = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['es'])
        sku_list_es = [dirr.split('/')[2] for dirr in directory_list_es]

        directory_list_uk = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['uk'])
        sku_list_uk = [dirr.split('/')[2] for dirr in directory_list_uk]

        directory_list_ita = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['ita'])
        sku_list_ita = [dirr.split('/')[2] for dirr in directory_list_ita]

        unique_skus = DataMerger.get_unique_skus_from_merged()

        for sku in unique_skus:
            product_ids = product_model.search([('x_sku', '=', sku)])

            if product_ids:
                attachment_paths = []

                # Remove 'VS' prefix [2:]
                if sku[2:] in sku_list_es:
                    attachment_paths = Util.get_all_files_in_directory(directory_list_es[sku_list_es.index(sku[2:])])
                elif sku[2:] in sku_list_uk:
                    attachment_paths = Util.get_all_files_in_directory(directory_list_uk[sku_list_uk.index(sku[2:])])
                elif sku[2:] in sku_list_ita:
                    attachment_paths = Util.get_all_files_in_directory(directory_list_ita[sku_list_ita.index(sku[2:])])

                if attachment_paths:
                    cls.logger.info(f"{sku}: UPLOADING {len(attachment_paths)} FILES")
                for attachment_path in attachment_paths:
                    with open(attachment_path, 'rb') as file:
                        pdf_binary_data = file.read()
                        encoded_data = base64.b64encode(pdf_binary_data).decode()

                    attachment_name = Util.translate_from_to_spanish('detect', attachment_path.split('\\')[-1])
                    attachment_name = f'{sku}_{attachment_name}'

                    existing_attachment = attachments_model.search([('name', '=', attachment_name), ('res_id', '=', product_ids[0])])

                    if existing_attachment:
                        cls.logger.info(f'{sku}: ATTACHMENT WITH NAME {attachment_name} ALREADY EXISTS IN ODOO')
                        continue

                    attachment_data = {
                        'name': attachment_name,
                        'datas': encoded_data,
                        'res_model': 'product.template',  # Model you want to link the attachment to (optional)
                        'res_id': product_ids[0],  # ID of the record of the above model you want to link the attachment to (optional)
                        'type': 'binary',
                    }

                    try:
                        attachment_id = attachments_model.create(attachment_data)
                        cls.logger.info(f'{sku}: ATTACHMENT WITH NAME {attachment_name} UPLOADED TO ODOO WITH ID {attachment_id}')
                    except HTTPError:
                        cls.logger.error(f"ERROR UPLOADING {attachment_name} FOR PRODUCT {sku}")
            else:
                cls.logger.warn(f'{sku} : NOT FOUND IN ODOO')

    @classmethod
    def import_imgs(cls):
        file_list = Util.get_all_files_in_directory(cls.PRODUCT_INFO_DIR)

        for file_path in file_list:
            with open(file_path, "r") as file:
                json_data = json.load(file)

            for product_data in json_data:
                if 'imgs' in product_data:
                    cls.logger.info(f'{product_data["sku"]}: FOUND {len(product_data["imgs"])} IMAGES')

                    # Search for the product template with the given sku
                    product_ids = cls.PRODUCT_MODEL.search([('x_sku', '=', product_data['sku'])])

                    if product_ids:
                        # write/overwrite the image to the product
                        if product_data['imgs']:
                            try:
                                cls.PRODUCT_MODEL.write([product_ids[0]], {'image_1920': product_data['imgs'][0]['img64']})
                            except RPCError:
                                pass

                            image_ids = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0]), ('image_1920', '!=', False)])

                            # Product existing images
                            images = cls.MEDIA_MODEL.browse(image_ids)
                            images = [image.image_1920 for image in images]

                            # Iterate over the products 'imgs'
                            for extra_img in product_data['imgs'][1:]:
                                if not images.__contains__(extra_img['img64']):
                                    name = f'{product_ids[0]}_{product_data["imgs"].index(extra_img)}'

                                    new_image = {
                                        'name': name,
                                        # Replace with your image name
                                        'image_1920': extra_img['img64'],
                                        'product_tmpl_id': product_ids[0]
                                    }
                                    try:
                                        # Create the new product.image record
                                        cls.MEDIA_MODEL.create(new_image)
                                        cls.logger.info(f'{product_data["sku"]}: UPLOADED IMAGE with name : {name}')
                                    except RPCError:
                                        pass
                                else:
                                    cls.logger.info(f'{product_data["sku"]}: Image already exists')

                            videos = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0]), ('video_url', '!=', False)])
                            videos = [video.video_url for video in videos]

                            if 'videos' in product_data:
                                # Iterate over the products 'videos'
                                for video_url in product_data['videos']:
                                    if not videos.__contains__(video_url):
                                        name = f'{product_ids[0]}_video_{product_data["videos"].index(video_url)}'

                                        new_video = {
                                            'name': name,
                                            # Replace with your image name
                                            'video_url': video_url,
                                            'product_tmpl_id': product_ids[0]
                                        }
                                        try:
                                            # Create the new product.image record
                                            cls.MEDIA_MODEL.create(new_video)
                                            cls.logger.info(f'{product_data["sku"]}: UPLOADED VIDEO url with name : {name}')
                                        except RPCError:
                                            pass
                                    else:
                                        cls.logger.info(f'{product_data["sku"]}: Image already exists')
                    else:
                        cls.logger.warn(f'{product_data["sku"]} : PRODUCT NOT FOUND IN ODOO')

                else:
                    cls.logger.warn(f'{product_data["sku"]} HAS NO IMAGES!')

    @classmethod
    def import_icons(cls):
        file_list = Util.get_all_files_in_directory(cls.PRODUCT_INFO_DIR)

        for file_path in file_list:
            with open(file_path, "r") as file:
                json_data = json.load(file)

        for product in json_data:
            if 'icons' in product:
                cls.logger.info(f'{product["sku"]} icons: {len(product["icons"])}')

                # Search for the product template with the given sku
                product_ids = cls.PRODUCT_MODEL.search([('x_sku', '=', product['sku'])])

                if product_ids:
                    image_ids = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0])])

                    # Product existing icons
                    images = cls.MEDIA_MODEL.browse(image_ids)

                    images = [image.image_1920 for image in images]

                    # Iterate over the products
                    for icon in product['icons']:
                        if not images.__contains__(icon):
                            name = f'{product_ids[0]}_{product["icons"].index(icon)}'
                            new_image = {
                                'name': name,  # Replace with your image name
                                'image_1920': icon,
                                'product_tmpl_id': product_ids[0]
                            }

                            try:
                                # Create the new product.image record
                                cls.MEDIA_MODEL.create(new_image)
                                cls.logger.info(f'{product["sku"]}: UPLOADED ICON with name : {name}')
                            except RPCError:
                                pass
                        else:
                            cls.logger.info('Icon already exists')
                else:
                    cls.logger.warn('PRODUCT NOT FOUND IN ODOO')

            else:
                cls.logger.warn(f'{product["sku"]} HAS NO ICONS!')

    @classmethod
    def import_fields(cls):
        # The 'ir.model.fields' model is used to create, read, and write fields in Odoo
        fields_model = cls.odoo.env['ir.model.fields']

        for new_field in Util.ODOO_CUSTOM_FIELDS:
            if fields_model.search([('name', '=', Util.format_field_odoo(new_field)), ('model', '=', 'product.template')]):
                cls.logger.info(f'Field {new_field} already exists in Odoo')
                continue

            # Create a dictionary for the custom field
            custom_field_data = {
                'name': Util.format_field_odoo(new_field),
                'ttype': 'char',
                'model': 'product.template',
                'model_id': cls.odoo.env['ir.model'].search([('model', '=', 'product.template')])[0],
                'state': 'manual',  # This field is being added manually, not through a module
                'field_description': new_field,
                'help': new_field
            }

            # Create the custom field in the Odoo instance
            new_field_id = fields_model.create(custom_field_data)
            cls.logger.info(f"Custom field '{new_field}' created with ID: {new_field_id}")
