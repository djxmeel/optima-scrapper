import copy
import os.path
from urllib.error import HTTPError

import odoorpc
import base64

from odoorpc.error import RPCError
from utils.util import Util


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

    PRODUCT_PDF_DIRS = {'es': 'data/vtac_spain/PRODUCT_PDF/',
                        'uk': 'data/vtac_uk/PRODUCT_PDF/',
                        'ita': 'data/vtac_italia/PRODUCT_PDF/'}

    # Fields not to create as attributes in ODOO
    NOT_ATTR_FIELDS = ('accesorios', 'videos', 'kit', 'icons', 'imgs', 'Ean', 'Código de familia', 'url', 'Sku')

    # TODO TEST the use of attribute_value IDs in assign_attribute_values()
    @classmethod
    def create_attributes_and_values(cls, attributes_values):
        created_attrs_values_ids = {}

        for name, value in attributes_values.items():
            existing_attr_ids  = cls.ATTRIBUTE_MODEL.search([('name', '=', name)])

            # Skip empty values
            if str(value).strip() == '':
                continue

            # Skip if the attribute already exists
            if existing_attr_ids:
                created_attrs_values_ids[existing_attr_ids[0]] = value
                continue

            # The attr to create
            attr = {
                'name': name,
                'create_variant': 'no_variant'  # Variants are created "always", "no_variant", or "dynamic"
            }

            # Saving the created IDs as keys in dict with their values
            created_attrs_values_ids[cls.ATTRIBUTE_MODEL.create(attr)] = value

        attr_values_to_create = []

        for id, value in created_attrs_values_ids.items():
            try:
                attr_val_ids = cls.ATTRIBUTE_VALUE_MODEL.search([('name', '=', value), ('attribute_id', '=', id)])

                if attr_val_ids:
                    created_attrs_values_ids[id] = attr_val_ids[0]
                    raise RPCError(f'Attribute\'s value {value} already exists')

                # Create attribute value and store value ID
                created_attrs_values_ids[id] = cls.ATTRIBUTE_VALUE_MODEL.create({
                    'name': value,
                    'attribute_id': id
                })
            except RPCError:
                pass

        return created_attrs_values_ids


    @classmethod
    def assign_attribute_values(cls, product_id, product, attributes_ids_values, update_mode=False):
        attr_lines = []

        for attribute_id, value_id in attributes_ids_values.items():
            # Only check if the attribute line already exists
            existing_lines = cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)])

            # Skip if the attribute line already exists
            if existing_lines:
                if update_mode:
                    # Delete existing lines with the same attribute and product
                    cls.ATTRIBUTE_LINE_MODEL.unlink(existing_lines)
                else:
                    continue

            # Create the attribute line
            attr_lines.append({
                    'product_tmpl_id': product_id,
                    'attribute_id': attribute_id,
                    'value_ids': [(6, 0, [value_id])]
                })

        try:
            cls.ATTRIBUTE_LINE_MODEL.create(attr_lines)
        except TypeError:
            cls.logger.info(f'ERROR ASSIGNING ATTRIBUTES TO PRODUCT WITH ID {product_id}')
            return

        cls.logger.info(f"FINISHED ASSIGNING {product['Sku']} ATTRIBUTES")


    @classmethod
    def import_products(cls, target_dir_path, uploaded_dir_path, skip_attrs_of_existing=False):
        file_list = Util.get_all_files_in_directory(target_dir_path)
        counter = 0
        for file_path in sorted(file_list):
            products = Util.load_json_data(file_path)

            cls.logger.info(f'IMPORTING PRODUCTS OF FILE : {file_path}')

            product_model = cls.PRODUCT_MODEL

            for product in products:
                counter += 1
                product_ids = cls.PRODUCT_MODEL.search([('x_sku', '=', product['Sku'])])

                attrs_to_create = {}
                temp_keys = list(product.keys())
                product_copy = copy.deepcopy(product)

                sku = product["Sku"]
                url = product["url"]

                for key in temp_keys:
                    if key not in Util.ODOO_SUPPORTED_FIELDS:
                        if key not in cls.NOT_ATTR_FIELDS:
                            attrs_to_create[key] = product[key]
                        if key not in Util.ODOO_CUSTOM_FIELDS:
                            del product[key]
                        else:
                            product[Util.format_field_odoo(key)] = product[key]
                            del product[key]

                if not product_ids:
                    created_attrs_ids_values = cls.create_attributes_and_values(attrs_to_create)

                    product_id = product_model.create(product)
                    cls.logger.info(f'Created product {sku} with origin URL : {url}')

                    cls.assign_attribute_values(product_id, product_copy, created_attrs_ids_values)
                else:
                    product_id = product_ids[0]
                    cls.logger.info(f'Product {sku} already exists in Odoo with id {product_ids[0]}')
                    if not skip_attrs_of_existing:
                        created_attrs_ids_values = cls.create_attributes_and_values(attrs_to_create)
                        cls.assign_attribute_values(product_id, product_copy, created_attrs_ids_values)

                cls.logger.info(f"PROCESSED : {counter} products\n")

            # Moving uploaded files to separate dir to persist progress
            Util.move_file_or_directory(file_path, f'{uploaded_dir_path}/{os.path.basename(file_path)}')

            cls.logger.info(f'IMPORTED PRODUCTS OF FILE : {file_path}')

        # Restoring target dir's original name
        Util.move_file_or_directory(uploaded_dir_path, target_dir_path, True)


    @classmethod
    def import_accessories(cls, target_dir_path):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        # Get the product template object
        acc_model = cls.odoo.env['x_accesorios_productos']


        # Delete all accessory model records
        # acc_model.unlink(acc_model.search([]))

        for file_path in sorted(file_list):
            products = Util.load_json_data(file_path)

            # Iterate over the products
            for product in products:
                accessories_sku = []

                if 'accesorios' in product:
                    if len(product['accesorios']) > 0:
                        print(len(product['accesorios']))

                if 'accesorios' in product and product['accesorios']:
                    for acc in product['accesorios']:
                        accessories_sku.append(acc)

                if accessories_sku:
                    # Search for the product template with the given name
                    main_product_id = cls.PRODUCT_MODEL.search([('x_sku', '=', product['Sku'])])
                    if main_product_id:
                        main_product_id = main_product_id[0]
                        cls.logger.info(f'SKU : {product["Sku"]} Accesorios : {len(accessories_sku)}')
                    else:
                        continue

                    for acc in accessories_sku:
                        existing_acc_ids = acc_model.search([('x_producto', '=', main_product_id), ('x_sku', '=', acc['Sku'])])

                        if existing_acc_ids:
                            cls.logger.info(f'UPDATED ACCESORIO OF PRODUCT WITH SKU {product["Sku"]} ID {main_product_id}')
                            updated_record_id = acc_model.write(existing_acc_ids[0], {'x_cantidad': acc['cantidad']})
                        else:
                            new_record_data = {
                                'x_referencia': acc['referencia'],
                                'x_producto': main_product_id,
                                'x_cantidad': acc['cantidad']
                            }

                            new_record_id = acc_model.create(new_record_data)
                            cls.logger.info(f'CREATED ACCESORIO OF PRODUCT WITH SKU {product["Sku"]} ID {main_product_id}')


    @classmethod
    def import_pdfs(cls, skus):
        product_model = cls.PRODUCT_MODEL
        attachments_model = cls.odoo.env['ir.attachment']

        directory_list_es = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['es'])
        sku_list_es = [dirr.split('/')[3] for dirr in directory_list_es]

        directory_list_uk = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['uk'])
        sku_list_uk = [dirr.split('/')[3] for dirr in directory_list_uk]

        directory_list_ita = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['ita'])
        sku_list_ita = [dirr.split('/')[3] for dirr in directory_list_ita]

        for sku in skus:
            product_ids = product_model.search([('x_sku', '=', sku)])

            if product_ids:
                attachment_paths = []

                if sku in sku_list_es:
                    attachment_paths = Util.get_all_files_in_directory(
                        directory_list_es[sku_list_es.index(sku)])
                elif sku in sku_list_uk:
                    attachment_paths = Util.get_all_files_in_directory(
                        directory_list_uk[sku_list_uk.index(sku)])
                elif sku in sku_list_ita:
                    attachment_paths = Util.get_all_files_in_directory(
                        directory_list_ita[sku_list_ita.index(sku)])

                if attachment_paths:
                    cls.logger.info(f"{sku}: UPLOADING {len(attachment_paths)} FILES")
                    for attachment_path in attachment_paths:
                        with open(attachment_path, 'rb') as file:
                            pdf_binary_data = file.read()
                            encoded_data = base64.b64encode(pdf_binary_data).decode()

                        attachment_name = attachment_path.split('\\')[-1]

                        try:
                            attachment_name = Util.translate_from_to_spanish('detect', attachment_name)
                        except:
                            pass

                        attachment_name = f'{sku}_{attachment_name}'

                        existing_attachment = attachments_model.search([('name', '=', attachment_name), ('res_id', '=', product_ids[0])])

                        if existing_attachment:
                            cls.logger.info(f'{sku}: ATTACHMENT WITH NAME {attachment_name} ALREADY EXISTS IN ODOO')
                            continue

                        attachment_data = {
                            'name': attachment_name,
                            'datas': encoded_data,
                            'res_model': 'product.template',  # Model you want to link the attachment to (optional)
                            'res_id': product_ids[0], # ID of the record of the above model you want to link the attachment to (optional)
                            'type': 'binary',
                        }

                        try:
                            attachment_id = attachments_model.create(attachment_data)
                            cls.logger.info(
                                f'{sku}: ATTACHMENT WITH NAME {attachment_name} UPLOADED TO ODOO WITH ID {attachment_id}')
                        except HTTPError or RPCError:
                            cls.logger.error(f"ERROR UPLOADING {attachment_name} FOR PRODUCT {sku}")
            else:
                cls.logger.warn(f'{sku} : NOT FOUND IN ODOO')


    @classmethod
    def import_imgs(cls, target_dir_path, uploaded_dir_path):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        for file_path in sorted(file_list):
            products = Util.load_json_data(file_path)

            for product in products:
                if 'imgs' in product:
                    cls.logger.info(f'{product["Sku"]}: FOUND {len(product["imgs"])} IMAGES')

                    # Search for the product template with the given sku
                    product_ids = cls.PRODUCT_MODEL.search([('x_sku', '=', product['Sku'])])

                    if product_ids:
                        # write/overwrite the image to the product
                        if product['imgs']:
                            try:
                                cls.PRODUCT_MODEL.write([product_ids[0]], {'image_1920': product['imgs'][0]['img64']})
                            except RPCError:
                                pass

                            image_ids = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0]), ('image_1920', '!=', False)])

                            # Product existing images
                            images = cls.MEDIA_MODEL.browse(image_ids)
                            images = [image.image_1920 for image in images]

                            # Iterate over the products 'imgs'
                            for extra_img in product['imgs'][1:]:
                                if not images.__contains__(extra_img['img64']):
                                    name = f'{product_ids[0]}_{product["imgs"].index(extra_img)}'

                                    new_image = {
                                        'name': name,
                                        'image_1920': extra_img['img64'],
                                        'product_tmpl_id': product_ids[0]
                                    }
                                    try:
                                        # Create the new product.image record
                                        cls.MEDIA_MODEL.create(new_image)
                                        cls.logger.info(f'{product["Sku"]}: UPLOADED IMAGE with name : {name}')
                                    except RPCError:
                                        cls.logger.info(f'{product["Sku"]}: ERROR UPLOADING IMAGE with name : {name} *{RPCError}*')
                                else:
                                    cls.logger.info(f'{product["Sku"]}: Image already exists')

                            cls.logger.info(f"{product['Sku']}:FINISHED UPLOADING IMAGES")

                            videos = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0]), ('video_url', '!=', False)])
                            videos = cls.MEDIA_MODEL.browse(videos)
                            videos = [video.video_url for video in videos]

                            if 'videos' in product:
                                # Iterate over the products 'videos'
                                for video_url in product['videos']:
                                    if not videos.__contains__(video_url):
                                        name = f'{product_ids[0]}_video_{product["videos"].index(video_url)}'

                                        new_video = {
                                            'name': name,
                                            'video_url': video_url,
                                            'product_tmpl_id': product_ids[0]
                                        }
                                        try:
                                            # Create the new product.image record
                                            cls.MEDIA_MODEL.create(new_video)
                                        except RPCError:
                                            pass
                                    else:
                                        cls.logger.info(f'{product["Sku"]}: Video already exists')

                                cls.logger.info(f"{product['Sku']}:FINISHED UPLOADING VIDEOS")
                    else:
                        cls.logger.warn(f'{product["Sku"]} : PRODUCT NOT FOUND IN ODOO')

                else:
                    cls.logger.warn(f'{product["Sku"]} HAS NO IMAGES!')

            # Moving uploaded files to separate dir to persist progress
            Util.move_file_or_directory(file_path, f'{uploaded_dir_path}/{os.path.basename(file_path)}')

        # Restoring target dir's original name
        Util.move_file_or_directory(uploaded_dir_path, target_dir_path, True)


    @classmethod
    def import_icons(cls, target_dir_path, uploaded_dir_path):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        for file_path in sorted(file_list):
            products = Util.load_json_data(file_path)

            for product in products:
                if 'icons' in product:
                    cls.logger.info(f'{product["Sku"]} icons: {len(product["icons"])}')

                    # Search for the product template with the given sku
                    product_ids = cls.PRODUCT_MODEL.search([('x_sku', '=', product['Sku'])])

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
                                    cls.logger.info(f'{product["Sku"]}: UPLOADED ICON with name : {name}')
                                except RPCError:
                                    pass
                            else:
                                cls.logger.info('Icon already exists')
                    else:
                        cls.logger.warn('PRODUCT NOT FOUND IN ODOO')

                else:
                    cls.logger.warn(f'{product["Sku"]} HAS NO ICONS!')

            # Moving uploaded files to separate dir to persist progress
            Util.move_file_or_directory(file_path, f'{uploaded_dir_path}/{os.path.basename(file_path)}')

        # Restoring target dir's original name
        Util.move_file_or_directory(uploaded_dir_path, target_dir_path, True)


    @classmethod
    def import_fields(cls, fields):
        # The 'ir.model.fields' model is used to create, read, and write fields in Odoo
        fields_model = cls.odoo.env['ir.model.fields']
        product_model_id = cls.odoo.env['ir.model'].search([('model', '=', 'product.template')])[0]

        for new_field in fields:
            new_field_formatted = Util.format_field_odoo(new_field)

            if fields_model.search([('name', '=', new_field_formatted), ('model', '=', 'product.template')]):
                cls.logger.info(f'Field {new_field} already exists in Odoo')
                continue

            # Create a dictionary for the custom field
            custom_field_data = {
                'name': new_field_formatted,
                'ttype': 'char',
                'model': 'product.template',
                'model_id': product_model_id,
                'state': 'manual',  # This field is being added manually, not through a module
                'field_description': new_field,
                'help': new_field
            }

            # Create the custom field in the Odoo instance
            new_field_id = fields_model.create(custom_field_data)
            cls.logger.info(f"Custom field '{new_field}' created with ID: {new_field_id}")
