import os.path
import time
from urllib.error import HTTPError, URLError

import odoorpc
import base64

import pandas as pd
from PIL import UnidentifiedImageError
from odoorpc.error import RPCError

from utils.loggers import Loggers
from utils.util import Util


class OdooImport:
    logger = Loggers.setup_odoo_import_logger()

    #odoo_host = 'trialdb-final2.odoo.com'
    odoo_host = 'optimaluz.soluntec.net'
    odoo_protocol = 'jsonrpc+ssl'
    odoo_port = '443'

    odoo_db = 'Pruebas'
    odoo_login = 'productos@optimaluz.com'
    odoo_pass = '96c04503fc98aa4ffd90a9cf72ceb2d90d709b01'

    #odoo_db = 'trialdb-final2'
    #odoo_login = 'itprotrial@outlook.com'
    #odoo_pass = 'itprotrial'

    odoo = odoorpc.ODOO(odoo_host, protocol=odoo_protocol, port=odoo_port)
    print("CONNECTED TO ODOO")

    # Authenticate with your credentials
    odoo.login(odoo_db, odoo_login, odoo_pass)
    print("LOGGED IN ODOO")

    ATTRIBUTE_MODEL = odoo.env['product.attribute']
    ATTRIBUTE_VALUE_MODEL = odoo.env['product.attribute.value']
    ATTRIBUTE_LINE_MODEL = odoo.env['product.template.attribute.line']

    MEDIA_MODEL = odoo.env['product.image']
    PRODUCT_MODEL = odoo.env['product.template']
    BRAND_MODEL = odoo.env['product.brand']

    PRODUCT_PUBLIC_CATEGORIES_MODEL = odoo.env['product.public.category']
    PRODUCT_INTERNAL_CATEGORY_MODEL = odoo.env['product.category']

    PRODUCT_PDF_DIRS = {'es': 'data/vtac_spain/PRODUCT_PDF',
                        'uk': 'data/vtac_uk/PRODUCT_PDF',
                        'ita': 'data/vtac_italia/PRODUCT_PDF'}

    PRODUCT_SPEC_SHEETS_DIR = 'data/vtac_uk/SPEC_SHEETS'

    # Fields not to create as attributes in ODOO
    NOT_ATTR_FIELDS = ('accesorios', 'videos', 'kit', 'icons', 'imgs', 'Ean', 'Código de familia', 'url', 'public_categories', 'transit', 'almacen2_custom', 'almacen3_custom', 'almacen1_custom', 'transit_stock_custom')

    # Invoice policy (delivery ; order)
    CURRENT_INVOICE_POLICY = 'delivery'

    # Product type (consu ; service ; product)
    PRODUCT_DETAILED_TYPE = 'product'

    # Product category (not eshop)
    PRODUCT_INTERNAL_CATEGORY = 'Productos de iluminación'

    # USE TO ONLY UPLOAD CERTAIN PRODUCTS
    PRIORITY_EXCEL_SKUS_PATH = 'data/common/excel/Productos Comprados o Vendidos VTAC.xlsx'

    # ID of the brand to assign to the products
    VTAC_BRAND_ID = 1

    @classmethod
    def create_internal_category(cls, internal_category):
        try:
            return cls.PRODUCT_INTERNAL_CATEGORY_MODEL.create({
                    'name': internal_category,
                    'property_cost_method': 'standard'
                })
        except RPCError:
            return None

    @classmethod
    def assign_public_categories(cls, product_id, public_categories):
        categ_ids = []
        for category in public_categories:
                categ_id = cls.PRODUCT_PUBLIC_CATEGORIES_MODEL.search([('name', '=', category)])
                if categ_id:
                    categ_ids.extend(categ_id)

        try:
            if categ_ids:
                cls.PRODUCT_MODEL.write(product_id, {'public_categ_ids': categ_ids})
                cls.logger.info(f"ASSIGNED Public categories {public_categories} to product with id {product_id}")
        except RPCError:
            cls.logger.warn(f"Public categories {public_categories} not assigned to product with id {product_id}")

    @classmethod
    def create_attributes_and_values(cls, attributes_values):
        created_attrs_values_ids = {}

        for name, value in attributes_values.items():
            existing_attr_ids = cls.ATTRIBUTE_MODEL.search([('name', '=', name)])

            # Skip empty values
            if not str(value).strip():
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

        for attr_id, value in created_attrs_values_ids.items():
            try:
                try:
                    attr_val_ids = cls.ATTRIBUTE_VALUE_MODEL.search([('name', '=', value), ('attribute_id', '=', attr_id)])
                except URLError:
                    time.sleep(5)
                    attr_val_ids = cls.ATTRIBUTE_VALUE_MODEL.search([('name', '=', value), ('attribute_id', '=', attr_id)])

                if attr_val_ids:
                    created_attrs_values_ids[attr_id] = attr_val_ids[0]
                    raise RPCError(f'Attribute\'s value {value} already exists')

                # Create attribute value and store value ID
                created_attrs_values_ids[attr_id] = cls.ATTRIBUTE_VALUE_MODEL.create({
                    'name': value,
                    'attribute_id': attr_id
                })
            except RPCError:
                pass

        return created_attrs_values_ids

    @classmethod
    def assign_brand(cls, product_id, product_brand_id):
        try:
            cls.PRODUCT_MODEL.write(product_id, {'product_brand_id': product_brand_id})
        except RPCError:
            cls.logger.warn(f"ID {product_id} : BRAND WAS NOT UPDATED")

    @classmethod
    def assign_internal_category(cls, product_id, product_internal_category):
        product_internal_category_id = cls.PRODUCT_INTERNAL_CATEGORY_MODEL.search([('name', '=', product_internal_category)])

        if not product_internal_category_id:
            cls.logger.warn("INTERNAL CATEGORY NOT FOUND IN ODOO")
            product_internal_category_id = [cls.create_internal_category(product_internal_category)]
            cls.logger.info(f"CREATED INTERNAL CATEGORY {product_internal_category} WITH ID {product_internal_category_id[0]}")

        cls.PRODUCT_MODEL.write(product_id, {'categ_id': product_internal_category_id[0]})
        cls.logger.info(f"ASSIGNED INTERNAL CATEGORY {product_internal_category} WITH ID {product_internal_category_id[0]}")

    @classmethod
    def assign_attribute_values(cls, product_id, product, attributes_ids_values, update_mode='no'):
        attr_lines = []

        if update_mode == 'deep':
            cls.ATTRIBUTE_LINE_MODEL.unlink(cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id)]))

        for attribute_id, value_id in attributes_ids_values.items():
            if update_mode == 'soft':
                try:
                    cls.ATTRIBUTE_LINE_MODEL.unlink(cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)]))
                except URLError:
                    time.sleep(5)
                    cls.ATTRIBUTE_LINE_MODEL.unlink(cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)]))
            else:
                try:
                    # Only check if the attribute line already exists
                    existing_lines = cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)])
                except URLError:
                    time.sleep(5)
                    existing_lines = cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)])

                # Skip if the attribute line already exists
                if existing_lines:
                    continue

            # Create the attribute line
            attr_lines.append({
                    'product_tmpl_id': product_id,
                    'attribute_id': attribute_id,
                    'value_ids': [(6, 0, [value_id])]
                })

        try:
            cls.ATTRIBUTE_LINE_MODEL.create(attr_lines)
        except (TypeError, RPCError):
            cls.logger.info(f'ERROR ASSIGNING ATTRIBUTES TO PRODUCT WITH ID {product_id}')
            return

        cls.logger.info(f"FINISHED ASSIGNING SKU {product['default_code']} ATTRIBUTES")

    @classmethod
    def import_products(cls, target_dir_path, uploaded_dir_path, skip_existing, use_priority_excel=False, force_update=False):
        file_list = Util.get_all_files_in_directory(target_dir_path)
        counter = 0

        PRIORITY_SKUS = Util.get_priority_excel_skus('data/common/excel/Productos Comprados o Vendidos VTAC.xlsx', 'A') if use_priority_excel else []
        skus_to_skip = Util.load_json("data/common/json/SKUS_TO_SKIP.json")["skus"]

        for file_path in sorted(file_list):
            products = Util.load_json(file_path)

            cls.logger.info(f'IMPORTING PRODUCTS OF FILE: {file_path}')

            for product in products:
                if product['default_code'] in skus_to_skip:
                    cls.logger.info(f"SKIPPING SKU {product['default_code']} INFO BECAUSE IT IS IN SKUS_TO_SKIP")
                    continue

                if use_priority_excel and product['default_code'] and product['default_code'] not in PRIORITY_SKUS:
                    cls.logger.info(f"SKIPPING SKU {product['default_code']} INFO BECAUSE IT IS NOT IN PRIORITY EXCEL")
                    continue

                # Removes videos from description
                if 'website_description' in product:
                    product['website_description'] = Util.remove_a_tags(product['website_description'])

                counter += 1
                product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'])])

                attrs_to_create = {}
                temp_keys = list(product.keys())

                try:
                    brand_id = cls.BRAND_MODEL.search([('name', '=', product['product_brand_id'])])
                except URLError:
                    time.sleep(5)
                    brand_id = cls.BRAND_MODEL.search([('name', '=', product['product_brand_id'])])


                if brand_id:
                    product['product_brand_id'] = brand_id[0]
                else:
                    del product['product_brand_id']
                    cls.logger.warn(f"PRODUCT BRAND {product['product_brand_id']} NOT FOUND IN ODOO")

                url = product["url"]

                for key in temp_keys:
                    if key not in Util.ODOO_SUPPORTED_FIELDS:
                        if key not in cls.NOT_ATTR_FIELDS:
                            attrs_to_create[key] = product[key]
                        if key not in Util.ODOO_CUSTOM_FIELDS:
                            del product[key]
                        else:
                            product[Util.format_odoo_custom_field_name(key)] = product[key]
                            del product[key]

                if not product_ids:
                    created_attrs_ids_values = cls.create_attributes_and_values(attrs_to_create)
                    try:
                        product_id = cls.PRODUCT_MODEL.create(product)
                        cls.logger.info(f'Created product {product["default_code"]} with origin URL : {url}')
                    except RPCError:
                        product['barcode'] = Util.randomize_barcode(product['barcode'])
                        product_id = cls.PRODUCT_MODEL.create(product)
                        cls.logger.info(f'Created product {product["default_code"]} with origin URL {url} with different barcode {product["barcode"]}')

                    cls.assign_internal_category(product_id, cls.PRODUCT_INTERNAL_CATEGORY)
                    cls.assign_attribute_values(product_id, product, created_attrs_ids_values)
                elif not skip_existing:
                    product_id = product_ids[0]

                    browsed_product = cls.PRODUCT_MODEL.browse(product_id)
                    current_origin_url = browsed_product.x_url

                    if not force_update and current_origin_url and (current_origin_url == url or 'v-tac.es' in current_origin_url or 'v-tac.es' not in url):
                        cls.logger.info(f'FORCE SKIPPING Product {product["default_code"]} for it\'s origin didn\'t change')
                        continue

                    try:
                        cls.logger.info(f'Updating existing product {product["default_code"]} with origin URL {url}')

                        cls.PRODUCT_MODEL.write(product_id, product)
                    except RPCError:
                        product['barcode'] = Util.randomize_barcode(product['barcode'])
                        cls.logger.info(f'Updating existing product {product["default_code"]} with origin URL {url} with different barcode {product["barcode"]}')
                        cls.PRODUCT_MODEL.write(product_id, product)

                    created_attrs_ids_values = cls.create_attributes_and_values(attrs_to_create)

                    cls.assign_internal_category(product_id, cls.PRODUCT_INTERNAL_CATEGORY)
                    cls.assign_attribute_values(product_id, product, created_attrs_ids_values, 'deep')

                    if 'product_brand_id' in product:
                        cls.assign_brand(product_id, product['product_brand_id'])
                else:
                    cls.logger.info(f'Product {product["default_code"]} already exists with origin URL {url}')

                cls.logger.info(f"PROCESSED: {counter} products\n")

            # Moving uploaded files to separate dir to persist progress
            Util.move_file_or_directory(file_path, f'{uploaded_dir_path}/{os.path.basename(file_path)}')

            cls.logger.info(f'IMPORTED PRODUCTS OF FILE: {file_path}')

        # Restoring target dir's original name
        Util.move_file_or_directory(uploaded_dir_path, target_dir_path, True)

    @classmethod
    def import_accessories(cls, target_dir_path):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        # Get the product template object
        acc_model = cls.odoo.env['x_accesorios_productos']

        # Delete all accessory model records
        acc_model.unlink(acc_model.search([]))

        for file_path in sorted(file_list):
            products = Util.load_json(file_path)

            # Iterate over the products
            for product in products:
                desc_extension = '<h3>Accesorios incluidos</h3><ul>'
                accessories_sku = []

                if 'accesorios' in product and product['accesorios']:
                    for acc in product['accesorios']:
                        accessories_sku.append(acc)

                if accessories_sku:
                    # Search for the product template with the given name
                    main_product_id = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'])])
                    if main_product_id:
                        main_product_id = main_product_id[0]
                        cls.logger.info(f'SKU: {product["default_code"]} Accesorios: {len(accessories_sku)}')
                    else:
                        cls.logger.info(f'SKU: {product["default_code"]} NOT FOUND IN ODOO')
                        continue

                    for acc in accessories_sku:
                        new_record_data = {
                            'x_default_code': acc['default_code'],
                            'x_producto': main_product_id,
                            'x_cantidad': acc['cantidad']
                        }

                        try:
                            new_record_id = acc_model.create(new_record_data)
                            cls.logger.info(f'CREATED ACCESORIO OF PRODUCT WITH SKU {product["default_code"]} ID {main_product_id}')

                            desc_extension += f'<li><b>Referencia: </b>{new_record_data["x_default_code"]}  <b>Cantidad: </b>{new_record_data["x_cantidad"]}</li>'

                        except RPCError:
                            cls.logger.info(f'{product["default_code"]} ERROR CREATING ACCESORIO')

                    desc_extension += '</ul>'

                    current_desc = cls.PRODUCT_MODEL.browse(main_product_id).website_description
                    current_desc = current_desc.split("<h3>Accesorios")[0]

                    cls.PRODUCT_MODEL.write(main_product_id, {'website_description': current_desc + desc_extension})

    @classmethod
    def import_spec_sheets(cls, clean, begin_from):
        product_model = cls.PRODUCT_MODEL
        attachments_model = cls.odoo.env['ir.attachment']

        skus_in_odoo = [p.default_code for p in cls.browse_all_products_in_batches('default_code', '!=', 'False')]

        directory_list = Util.get_nested_directories(cls.PRODUCT_SPEC_SHEETS_DIR)
        spec_sheets_skus = [dirr.split('\\')[-1] for dirr in directory_list]

        for index, sku in enumerate(skus_in_odoo[begin_from:]):
            product_id = product_model.search([('default_code', '=', sku)])[0]
            spec_sheet_name_template = 'FICHA_TECNICA_SKU_{}.pdf'

            try:
                spec_sheet_path = Util.get_all_files_in_directory(directory_list[spec_sheets_skus.index(sku)])
            except ValueError:
                cls.logger.warn(f"SKIPPING {sku} BECAUSE IT HAS NO SPEC SHEET")
                continue

            existing_spec_sheet = attachments_model.search([('name', '=', spec_sheet_name_template.format(sku))])

            if clean:
                attachments_model.unlink(existing_spec_sheet)
                existing_spec_sheet.clear()

            print(f'{index + begin_from + 1} / {len(skus_in_odoo[begin_from:])}')

            if existing_spec_sheet:
                cls.logger.warn(f"SKIPPING {sku} BECAUSE IT HAS SPEC SHEET UPLOADED")
                continue

            if spec_sheet_path:
                cls.logger.info(f"{sku}: UPLOADING SPEC SHEET")

                for attachment_path in spec_sheet_path:
                    with open(attachment_path, 'rb') as file:
                        pdf_binary_data = file.read()
                        encoded_data = base64.b64encode(pdf_binary_data).decode()

                    attachment_name = attachment_path.split('\\')[-1]

                    attachment_data = {
                        'name': attachment_name,
                        'website_name': 'Ficha técnica.pdf',
                        'datas': encoded_data,
                        'public': True,
                        'attached_in_product_tmpl_ids': [product_id],
                        'type': 'binary'
                    }

                    try:
                        attachment_id = attachments_model.create(attachment_data)
                        cls.logger.info(f'{sku}: {attachment_name} UPLOADED TO ODOO WITH ID {attachment_id}')
                    except TimeoutError:
                        cls.logger.error(f"{sku}: FAILED TO UPLOAD {attachment_name} FOR PRODUCT")
                        time.sleep(10)
                        cls.import_spec_sheets(clean, begin_from)
                    except HTTPError:
                        cls.logger.error(f"HTTP ERROR: FILE {attachment_name} POTENTIALLY TOO BIG. CONTINUING")
                        continue

    @classmethod
    def import_pdfs(cls, begin_from=0, clean=False, skip_products_w_attachments=False):
        product_model = cls.PRODUCT_MODEL
        attachments_model = cls.odoo.env['ir.attachment']

        skus_in_odoo = [p.default_code for p in cls.browse_all_products_in_batches('default_code', '!=', 'False')]

        directory_list_es = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['es'])
        sku_list_es = [dirr.split('\\')[-1] for dirr in directory_list_es]

        directory_list_uk = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['uk'])
        sku_list_uk = [dirr.split('\\')[-1] for dirr in directory_list_uk]

        directory_list_ita = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['ita'])
        sku_list_ita = [dirr.split('\\')[-1] for dirr in directory_list_ita]

        for index, sku in enumerate(skus_in_odoo[begin_from:]):
            product_id = product_model.search([('default_code', '=', sku)])[0]

            if clean:
                atts = attachments_model.search([('attached_in_product_tmpl_ids', '=', [product_id]), ('website_name', '!=', 'Ficha Técnica')])
                attachments_model.unlink(atts)
                cls.logger.info(f"CLEANED ATTACHMENTS OF SKU {sku}")

            print(f'{index + begin_from + 1} / {len(skus_in_odoo)}')

            if skip_products_w_attachments and not clean:
                product_uploaded_attachments = attachments_model.search([('attached_in_product_tmpl_ids', '=', [product_id]), ('website_name', '!=', 'Ficha Técnica')])

                if product_uploaded_attachments:
                    cls.logger.warn(f"SKIPPING {sku} BECAUSE IT HAS ATTACHMENTS UPLOADED")
                    continue

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

                    existing_attachment = attachments_model.search([('name', '=', f'{sku}_{attachment_name}'), ('attached_in_product_tmpl_ids', '=', [product_id])])

                    if existing_attachment:
                        cls.logger.info(f'{sku}: ATTACHMENT WITH NAME {sku}_{attachment_name} ALREADY EXISTS IN ODOO')
                        continue

                    attachment_data = {
                        'name': f'{sku}_{attachment_name}',
                        'website_name': attachment_name,
                        'datas': encoded_data,
                        'public': True,
                        'attached_in_product_tmpl_ids': [product_id],
                        'type': 'binary'
                    }

                    try:
                        attachment_id = attachments_model.create(attachment_data)
                        cls.logger.info(
                            f'{sku}: ATTACHMENT WITH NAME {attachment_name} UPLOADED TO ODOO WITH ID {attachment_id}')
                    except TimeoutError:
                        cls.logger.error(f"FAILED TO UPLOAD {attachment_name} FOR PRODUCT {sku}")
                        time.sleep(10)
                        cls.import_pdfs(begin_from, skip_products_w_attachments, clean)
                    except HTTPError:
                        cls.logger.error(f"HTTP ERROR: FILE {attachment_name} POTENTIALLY TOO BIG. CONTINUING")
                        continue

    @classmethod
    def import_imgs_videos(cls, target_dir_path, uploaded_dir_path, skip_products_with_images, clean=False):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        for file_path in sorted(file_list):
            products = Util.load_json(file_path)

            for product in products:

                try:
                    # Search for the product template with the given sku
                    product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'].strip())])
                except URLError:
                    time.sleep(5)
                    product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'].strip())])

                if product_ids:
                    browsed_product = cls.PRODUCT_MODEL.browse(product_ids[0])
                else:
                    cls.logger.warn(f'{product["default_code"]} NOT FOUND IN ODOO')
                    continue

                if 'videos' in product:
                    videos = cls.MEDIA_MODEL.search(
                        [('product_tmpl_id', '=', product_ids[0]), ('video_url', '!=', False)])

                    if videos and clean:
                        cls.MEDIA_MODEL.unlink(videos)
                        cls.logger.info(f"CLEANED VIDEOS OF SKU {product['default_code']}")
                        videos.clear()
                    else:
                        videos = cls.MEDIA_MODEL.browse(videos)
                        videos = [video.video_url for video in videos]

                    # Iterate over the products 'videos'
                    for video_url in product['videos']:
                        if video_url not in videos:
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
                            cls.logger.info(f'{product["default_code"]}: Video already exists')

                    cls.logger.info(f"{product['default_code']}:FINISHED UPLOADING VIDEOS")

                if 'imgs' in product and product['imgs']:
                    cls.logger.info(f'{product["default_code"]}: FOUND {len(product["imgs"])} IMAGES')

                    images = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0]), ('image_1920', '!=', False)])
                    if images:
                        if clean and not browsed_product.x_lock_main_media:
                            cls.MEDIA_MODEL.unlink(images)
                            images.clear()
                            images = []
                            cls.logger.info(f"CLEANED IMAGES OF SKU {product['default_code']}")

                        if skip_products_with_images:
                            cls.logger.warn(f"SKIPPING {product['default_code']} BECAUSE IT HAS IMAGES UPLOADED")
                            time.sleep(0.3)
                            continue
                        else:
                            # Product existing images
                            images = cls.MEDIA_MODEL.browse(images)
                            images = [image.image_1920 for image in images]

                    # write/overwrite the image to the product
                    try:
                        if not browsed_product.x_lock_main_media:
                            cls.PRODUCT_MODEL.write([product_ids[0]], {'image_1920': product['imgs'][0]['img64']})
                            product['imgs'].pop(0)
                    except RPCError:
                        pass

                    try:
                        # Resize images to 1920px width for Odoo
                        product['imgs'] = [Util.resize_image_b64(img['img64'], 1920) for img in product['imgs']]
                    except UnidentifiedImageError:
                        cls.logger.error(f"ERROR RESIZING IMAGE {product['default_code']}")
                        pass

                    # Iterate over the products 'imgs'
                    for extra_img in product['imgs']:
                        if extra_img not in images:
                            name = f"{product_ids[0]}_{product['imgs'].index(extra_img)}"

                            new_image = {
                                'name': name,
                                'image_1920': extra_img,
                                'product_tmpl_id': product_ids[0]
                            }
                            try:
                                # Create the new product.image record
                                cls.MEDIA_MODEL.create(new_image)
                            except RPCError:
                                cls.logger.info(f'{product["default_code"]}: ERROR UPLOADING IMAGE with name : {name}')
                        else:
                            cls.logger.info(f'{product["default_code"]}: Image already exists')

                    cls.logger.info(f"{product['default_code']}:FINISHED UPLOADING IMAGES")
                else:
                    cls.logger.warn(f'{product["default_code"]} HAS NO IMAGES!')

            # Moving uploaded files to separate dir to persist progress
            Util.move_file_or_directory(file_path, f'{uploaded_dir_path}/{os.path.basename(file_path)}')

        # Restoring target dir's original name
        Util.move_file_or_directory(uploaded_dir_path, target_dir_path, True)


    @classmethod
    def import_icons(cls, begin_from=0):
        # Try getting icons from EXCEL for products of catalog
        icons_excel = Util.load_excel_columns_in_dictionary_list('data/common/excel/product_icons.xlsx')
        products_odoo = cls.browse_all_products_in_batches('default_code', '!=', False)

        for product in products_odoo[begin_from:]:
            icons_b64 = []
            for record in icons_excel:
                if str(record['SKU']) == product.default_code:
                    if not pd.isna(record['ICONS']):
                        icons_b64 = Util.get_encoded_icons_from_excel(str(record['ICONS']).split(','))
                    break
            try:
                # Add V-TAC LOGO icon to all V-TAC products
                if product.product_brand_id.name == 'V-TAC':
                    icons_b64.insert(0, Util.get_vtac_logo_icon_b64()['vtaclogo'])
            except URLError:
                time.sleep(5)
                if product.product_brand_id.name == 'V-TAC':
                    icons_b64.insert(0, Util.get_vtac_logo_icon_b64()['vtaclogo'])

            cls.logger.info(f'{product.default_code}: {len(icons_b64)} ICONS')

            if icons_b64:
                # Resize icons to 1920px width for Odoo
                icons_b64 = [Util.resize_image_b64(icon, 1920) for icon in icons_b64]

                # Iterate over the products
                for index, icon in enumerate(icons_b64):
                    name = f'icon_{product.id}_{icons_b64.index(icon)}'

                    try:
                        if index + 1 > 8:
                            cls.logger.warn(f'{product.default_code}: ICONS LIMIT of 8 REACHED')
                            break
                        try:
                            # Create the new product.image record
                            cls.PRODUCT_MODEL.write(product.id, {f'x_icono{index + 1}': icon})
                        except URLError:
                            time.sleep(5)
                            cls.PRODUCT_MODEL.write(product.id, {f'x_icono{index + 1}': icon})

                        if index + 1 == len(icons_b64):
                            cls.logger.info(f'{product.default_code}: ICONS UPLOADED')
                            # Remove not used icon fields
                            for i in range(index + 2, 9):
                                cls.PRODUCT_MODEL.write([product.id], {f'x_icono{i}': False})
                    except RPCError:
                        cls.logger.warn(f'{product.default_code}: ERROR UPLOADING ICON with name : {name}')

    @classmethod
    def import_fields(cls, fields):
        # The 'ir.model.fields' model is used to create, read, and write fields in Odoo
        fields_model = cls.odoo.env['ir.model.fields']
        product_model_id = cls.odoo.env['ir.model'].search([('model', '=', 'product.template')])[0]

        for new_field in fields:
            new_field_formatted = Util.format_odoo_custom_field_name(new_field)

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

    @classmethod
    def import_public_categories(cls, products_public_categories_path, begin_from_row=0):
        products_public_categories = Util.load_excel_columns_in_dictionary_list(products_public_categories_path)
        public_categories_model = cls.odoo.env['product.public.category']

        max_child_categ_number = 4

        for index, product in enumerate(products_public_categories[begin_from_row:]):
            public_categories = []

            try:
                product_id = cls.PRODUCT_MODEL.search([('default_code', '=', product['SKU'])])[0]
            except URLError:
                time.sleep(5)
                product_id = cls.PRODUCT_MODEL.search([('default_code', '=', product['SKU'])])[0]
            except IndexError:
                cls.logger.warn(f"PRODUCT WITH SKU {product['SKU']} NOT FOUND IN ODOO")
                continue

            for i in range(1, max_child_categ_number + 1):
                try:
                    categ = public_categories_model.search([('name', '=', str(product[f"CATEGORY {i}"]).strip()), ('parent_id.name', '=', str(product["parent"]).strip())])
                    if categ:
                        public_categories.append(categ[0])
                    else:
                        if not pd.isna(product[f'CATEGORY {i}']):
                            cls.logger.warn(f"CATEGORY {product[f'CATEGORY {i}']} NOT FOUND IN ODOO")
                except URLError:
                    time.sleep(5)
                    categ = public_categories_model.search([('name', '=', str(product[f"CATEGORY {i}"]).strip()), ('parent_id.name', '=', str(product["parent"]).strip())])
                    if categ:
                        public_categories.append(categ[0])
                    else:
                        if not pd.isna(product[f'CATEGORY {i}']):
                            cls.logger.warn(f"CATEGORY {product[f'CATEGORY {i}']} NOT FOUND IN ODOO")

            for categ in public_categories:
                try:
                    cls.PRODUCT_MODEL.write(product_id, {'public_categ_ids': [(4, categ)]})
                except URLError:
                    time.sleep(5)
                    cls.PRODUCT_MODEL.write(product_id, {'public_categ_ids': [(4, categ)]})
                cls.logger.info(f"ASSIGNED CATEGORY_ID {categ} TO SKU {product['SKU']}")
            cls.logger.info(f"{index + 1 + begin_from_row} / {len(products_public_categories)}")

    @classmethod
    def browse_all_products_in_batches(cls, field=None, operator=None, value=None):
        # Fetch records in batches to avoid RPCerror
        batch_size = 100
        offset = 0
        products = []

        while True:
            if not field or not operator:
                if Util.ODOO_FETCHED_PRODUCTS:
                    cls.logger.info(f"FOUND {len(Util.ODOO_FETCHED_PRODUCTS)} LOADED PRODUCTS IN MEMORY")
                    return Util.ODOO_FETCHED_PRODUCTS
                try:
                    product_ids = cls.PRODUCT_MODEL.search([], offset=offset, limit=batch_size)
                except URLError:
                    time.sleep(5)
                    product_ids = cls.PRODUCT_MODEL.search([], offset=offset, limit=batch_size)
            else:
                try:
                    product_ids = cls.PRODUCT_MODEL.search([(field, operator, value)], offset=offset, limit=batch_size)
                except URLError:
                    time.sleep(5)
                    product_ids = cls.PRODUCT_MODEL.search([(field, operator, value)], offset=offset, limit=batch_size)
            if not product_ids:  # Exit the loop when no more records are found
                break

            offset += batch_size
            try:
                products.extend(cls.PRODUCT_MODEL.browse(product_ids))
                cls.logger.info(f"FETCHED PRODUCTS: {len(products)}")
            except TimeoutError:
                cls.logger.error(f"TIMEOUT ERROR FETCHING PRODUCTS. RETRYING IN 5 SECONDS...")
                time.sleep(5)
                products.extend(cls.PRODUCT_MODEL.browse(product_ids))
            except HTTPError:
                cls.logger.error(f"HTTP ERROR FETCHING PRODUCTS. RETRYING IN 20 SECONDS...")
                time.sleep(20)
                products.extend(cls.PRODUCT_MODEL.browse(product_ids))

        if not field or not operator:
            cls.logger.info(f"FETCHED ALL PRODUCTS: {len(products)}")
            Util.ODOO_FETCHED_PRODUCTS.extend(products)

        return products

    @classmethod
    def import_supplier_info(cls, supplier_stock_excel_path, supplier_pricelist_excel_path, update_mode=False):
        supplier_info_model = cls.odoo.env['product.supplierinfo']
        partner_model = cls.odoo.env['res.partner']
        partner_id = partner_model.search([('name', '=', 'V-TAC Europe Ltd.')])[0]

        products = cls.browse_all_products_in_batches('default_code', '!=', False)
        stock_excel_dicts = Util.load_excel_columns_in_dictionary_list(supplier_stock_excel_path)
        pricelist_excel_dicts = Util.load_excel_columns_in_dictionary_list(supplier_pricelist_excel_path)

        for product in products:
            if ']' in product.name:
                supplier_prod_name = str(product.name).split(']')[1].strip()
            else:
                supplier_prod_name = str(product.name)
            purchase_price = 0

            for line in pricelist_excel_dicts:
                if str(line['SKU']) == product.default_code:
                    purchase_price = line['PRECIO COMPRA']
                    supplier_prod_name = line['PRODUCTO']
                    cls.PRODUCT_MODEL.write(product.id, {'standard_price': line['COSTE']})
                    break

            if not supplier_prod_name:
                for line in stock_excel_dicts:
                    if str(line['SKU']) == product.default_code and line['name']:
                        supplier_prod_name = line['PRODUCTO']
                        break

            product_suppl_info_ids = supplier_info_model.search([('product_tmpl_id', '=', product.id)])

            if product_suppl_info_ids:
                if update_mode and purchase_price > 0:
                    supplier_info_model.write(product_suppl_info_ids[0], {
                        'product_name': supplier_prod_name,
                        'partner_id': partner_id,
                        'product_tmpl_id': product.id,
                        'product_code': product.default_code,
                        'price': purchase_price,
                        'min_qty': 1
                    })
                    cls.logger.info(f"UPDATED SUPPLIER INFO FOR PRODUCT {product.default_code}")
                else:
                    cls.logger.info(f"SKIPPING PRODUCT {product.default_code} BECAUSE IT ALREADY HAS SUPPLIER INFO")
                continue

            supplier_info_model.create({
                'product_name': supplier_prod_name,
                'partner_id': partner_id,
                'product_tmpl_id': product.id,
                'product_code': product.default_code,
                'price': purchase_price,
                'min_qty': 1
            })

            cls.logger.info(f"CREATED SUPPLIER INFO FOR PRODUCT {product.default_code}")

    @classmethod
    def import_descatalogados_catalogo(cls, skus_catalogo_file_path):
        skus = [str(entry['SKU']) for entry in Util.load_excel_columns_in_dictionary_list(skus_catalogo_file_path)]

        products = cls.browse_all_products_in_batches('product_brand_id', '=', cls.VTAC_BRAND_ID)

        for index, product in enumerate(products):
            if str(product.default_code) not in skus:
                if product.description_purchase and "WEB" in product.description_purchase:
                    description_purchase = "DESCATALOGADO CATALOGO - DESCATALOGADO WEB"
                else:
                    description_purchase = "DESCATALOGADO CATALOGO"

                cls.PRODUCT_MODEL.write(product.id,
                                        {'description_purchase': description_purchase,
                                         'name': str(product.name).replace('[VSD','[VS').replace('[VS', '[VSD')})
                cls.logger.info(f"{index+1}. {product.default_code}: CHANGED IN-NAME REF FROM VS TO VSD")
            else:
                cls.PRODUCT_MODEL.write(product.id,{'name': str(product.name).replace('[VSD', '[VS')})
                cls.logger.info(f"{index+1}. {product.default_code} SKIPPING BECAUSE IT IS IN CATALOGO")

    @classmethod
    def import_brands(cls, brands_excel_file_path):
        brand_names = [str(entry['name']) for entry in Util.load_excel_columns_in_dictionary_list(brands_excel_file_path)]

        for brand_name in brand_names:
            if cls.BRAND_MODEL.search([('name', '=', brand_name)]):
                cls.logger.info(f"BRAND {brand_name} ALREADY EXISTS IN ODOO")
                continue

            cls.BRAND_MODEL.create({'name': brand_name})
            cls.logger.info(f"CREATED BRAND {brand_name}")

    @classmethod
    def archive_products_from_json(cls, product_to_archive_conditions_json_path):
        product_to_archive_conditions = Util.load_json(product_to_archive_conditions_json_path)

        for attr, value in product_to_archive_conditions.items():
            cls.archive_products_based_on_condition(attr, '=', value)

    @classmethod
    def archive_products_based_on_condition(cls, attribute, condition, value):
        products_to_archive = cls.PRODUCT_MODEL.search([
            ('attribute_line_ids.attribute_id.name', '=', attribute),
            ('attribute_line_ids.value_ids.name', condition, value)
        ])

        for product in cls.PRODUCT_MODEL.browse(products_to_archive):
            if not product.active:
                continue
            product.write({'active': False})  # This archives the product in the database

    @classmethod
    def update_product_availability(cls, product, eu_stock):
        sku_dict = {}

        for row in eu_stock:
            sku_dict[str(row['SKU'])] = row

        eu_stock = sku_dict

        buyled_stock = cls.get_buyled_stock(product['default_code'])
        product['almacen3_custom'] = buyled_stock['ita']
        product['transit_stock_custom'] = buyled_stock['bled']

        uk_stock = cls.get_uk_stock(product['default_code'])
        product['almacen2_custom'] = uk_stock['uk']
        product['transit'] = uk_stock['transit']

        all_eu_stock_quant = product['almacen2_custom'] + product['almacen3_custom']

        product['Entrada de nuevas unidades'] = ''

        if product['default_code'] in eu_stock:
            try:
                if int(eu_stock[product['default_code']]['AVAILABLE']) > 0:
                    product['almacen1_custom'] = int(eu_stock[product['default_code']]['AVAILABLE'])
            except ValueError:
                pass

            if not pd.isna(eu_stock[product['default_code']]['UNDELIVERED ORDER']):
                product['Entrada de nuevas unidades'] = f"Próximamente"

                if not pd.isna(eu_stock[product['default_code']]['next delivery']) and '-' in str(eu_stock[product['default_code']]['next delivery']):
                    date_unformatted = str(eu_stock[product["default_code"]]["next delivery"])[:10]
                    product['Entrada de nuevas unidades'] = '/'.join(date_unformatted.split('-')[::-1])

        if product['transit'] > 0:
            if not product['Entrada de nuevas unidades']:
                product['Entrada de nuevas unidades'] = f"Próximamente"
            product['Entrada de nuevas unidades'] = f'{product["Entrada de nuevas unidades"]} ({product["transit"]} unidades)'

        product['Stock europeo'] = f"{product['almacen1_custom'] + all_eu_stock_quant}"

        return product

    @classmethod
    def clear_availability_attributes(cls, product_id, eu_stock_attr_id, entradas_attr_id):
        cls.ATTRIBUTE_LINE_MODEL.unlink(cls.ATTRIBUTE_LINE_MODEL.search([('attribute_id', '=', eu_stock_attr_id), ('product_tmpl_id', '=', product_id)]) +
                                        cls.ATTRIBUTE_LINE_MODEL.search([('attribute_id', '=', entradas_attr_id), ('product_tmpl_id', '=', product_id)]))

    @classmethod
    def import_availability_vtac(cls, eu_stock_excel_path, generate_missing_products_excel, begin_from):
        products = cls.browse_all_products_in_batches('product_brand_id', '=', cls.VTAC_BRAND_ID)
        eu_stock = Util.load_excel_columns_in_dictionary_list(eu_stock_excel_path)
        eu_stock_attr_id = cls.ATTRIBUTE_MODEL.search([('name', '=', 'Stock europeo')])[0]
        entradas_attr_id = cls.ATTRIBUTE_MODEL.search([('name', '=', 'Entrada de nuevas unidades')])[0]

        if generate_missing_products_excel:
            cls.generate_missing_products_excel(products, eu_stock)

        for index, product in enumerate(products[begin_from:]):
            try:
                # Skip blistered
                if '-E' in products.default_code:
                    continue

                cls.clear_availability_attributes(product.id, eu_stock_attr_id, entradas_attr_id)

                product_dict = {'default_code': product.default_code,
                                'description_purchase': product.description_purchase,
                                'qty_available': product.qty_available,
                                'categ_id': product.categ_id,
                                'id': product.id,
                                'name': product.name,
                                'Stock europeo': "0 unidades (Disponible para envío en un plazo de 6 a 9 días hábiles)",
                                'transit': product.x_transit,
                                'almacen1_custom': product.x_almacen1_custom,
                                'almacen2_custom': product.x_almacen2_custom,
                                'almacen3_custom': product.x_almacen3_custom,
                                'transit_stock_custom': product.x_transit_stock_custom
                                }

                product_dict = cls.update_product_availability(product_dict, eu_stock)

                cls.PRODUCT_MODEL.write(product.id, {'x_transit': product_dict['transit'],
                                                     'x_almacen1_custom': product_dict['almacen1_custom'],
                                                     'x_almacen2_custom': product_dict['almacen2_custom'],
                                                     'x_almacen3_custom': product_dict['almacen3_custom'],
                                                     'x_transit_stock_custom': product_dict['transit_stock_custom']})

                attr_ids_values = cls.create_attributes_and_values({'Stock europeo': f"{product_dict['Stock europeo']} unidades (Disponible para envío en un plazo de 6 a 9 días hábiles)",
                                                                    'Stock en tránsito': f'{product_dict["transit_stock_custom"]} unidades (Disponible para envío en un plazo de 1 a 2 días hábiles)',
                                                                    '- Almacén 1': f'{product_dict["almacen1_custom"]} unidades',
                                                                    '- Almacén 2': f'{product_dict["almacen2_custom"]} unidades',
                                                                    '- Almacén 3': f'{product_dict["almacen3_custom"]} unidades',
                                                                    'Entrada de nuevas unidades': product_dict['Entrada de nuevas unidades']
                                                                    })

                cls.assign_attribute_values(product.id, product, attr_ids_values, 'soft')

                cls.update_availability_related_fields(product_dict)

                cls.logger.info(f"UPDATED PRODUCT {product.default_code} AVAILABILITY {index + begin_from + 1} / {len(products)}")
            except URLError as e:
                cls.logger.error(f"ERROR UPDATING PRODUCT {product.default_code} AVAILABILITY. RETRYING...")
                time.sleep(60)
                cls.import_availability_vtac(eu_stock_excel_path, generate_missing_products_excel, index + begin_from)

    @classmethod
    def update_availability_related_fields(cls, product_dict):
        stock_europeo = product_dict['Stock europeo'].split(" ")[0]
        out_of_stock_messages = Util.load_json('data/common/json/VTAC_OOS_MSGS.json')['oos']
        skus_to_not_publish = Util.load_json('data/common/json/SKUS_TO_NOT_PUBLISH.json')['skus']
        productos_iluminacion_category_id = cls.odoo.env['product.category'].search([('name', '=', 'Productos de iluminación')])[0]

        # TEMP set to true when ready to publish
        is_published = False
        allow_out_of_stock_order = True
        out_of_stock_msg = out_of_stock_messages[3]

        if product_dict['default_code'] in skus_to_not_publish:
            is_published = False

        if stock_europeo == '0':
            allow_out_of_stock_order = False

            if 'Próximamente' in product_dict['Entrada de nuevas unidades']:
                out_of_stock_msg = out_of_stock_messages[2]
            elif '/' in product_dict['Entrada de nuevas unidades']:
                out_of_stock_msg = out_of_stock_messages[1]

            if '[VSD' in product_dict['name']:
                is_published = False
        else:
            out_of_stock_msg = out_of_stock_messages[0]

        # Unpublish products that are not in the 'Productos de iluminación' category
        if product_dict['categ_id'] != productos_iluminacion_category_id:
            is_published = False

        cls.PRODUCT_MODEL.write(product_dict["id"], {'allow_out_of_stock_order': allow_out_of_stock_order,
                                                        'out_of_stock_message': out_of_stock_msg,
                                                        'is_published': is_published})

    @classmethod
    def import_local_stock(cls, local_stock_excel_path):
        stock_quant_model = cls.odoo.env['stock.quant']

        products = cls.browse_all_products_in_batches()
        local_stock_excel_dicts = Util.load_excel_columns_in_dictionary_list(local_stock_excel_path)
        try:
            location_id = cls.odoo.env['stock.location'].search([('name', '=', 'Stock')])[0]
        except URLError:
            time.sleep(5)
            location_id = cls.odoo.env['stock.location'].search([('name', '=', 'Stock')])[0]

        for product in products:
            quantity = 0

            for line in local_stock_excel_dicts:
                if str(line['SKU']) == product.default_code:
                    quantity = line['Cantidad']
                    break
            try:
                product_stock_quant_ids = stock_quant_model.search([('product_id', '=', product.id)])
            except URLError:
                time.sleep(5)
                product_stock_quant_ids = stock_quant_model.search([('product_id', '=', product.id)])

            if product_stock_quant_ids:
                try:
                    stock_quant_model.write(product_stock_quant_ids[0], {
                        'inventory_quantity': quantity,
                        'product_id': product.id,
                        'location_id': location_id
                    })
                    cls.logger.info(f"UPDATED STOCK QUANT FOR PRODUCT {product.default_code} WITH QUANTITY {quantity}")
                except URLError:
                    time.sleep(5)
                    stock_quant_model.write(product_stock_quant_ids[0], {
                        'inventory_quantity': quantity,
                        'product_id': product.id,
                        'location_id': location_id
                    })
                    cls.logger.info(f"UPDATED STOCK QUANT FOR PRODUCT {product.default_code} WITH QUANTITY {quantity}")
            else:
                try:
                    product_stock_quant_ids = stock_quant_model.create({
                        'inventory_quantity': quantity,
                        'product_id': product.id,
                        'location_id': location_id
                    })
                    cls.logger.info(f"CREATED STOCK QUANT FOR PRODUCT {product.default_code} WITH QUANTITY {quantity}")
                except RPCError:
                    cls.logger.warn(f"ERROR CREATING STOCK QUANT FOR PRODUCT {product.default_code}")
                    continue
                except URLError:
                    time.sleep(5)
                    product_stock_quant_ids = stock_quant_model.create({
                        'inventory_quantity': quantity,
                        'product_id': product.id,
                        'location_id': location_id
                    })
                    cls.logger.info(f"CREATED STOCK QUANT FOR PRODUCT {product.default_code} WITH QUANTITY {quantity}")
            try:
                stock_quant_model.action_apply_inventory(product_stock_quant_ids)
            except URLError:
                time.sleep(5)
                stock_quant_model.action_apply_inventory(product_stock_quant_ids)

    @classmethod
    def import_correct_names_from_excel(cls, excel_path, get_from_jsons):
        if get_from_jsons:
            products_dicts = Util.load_data_in_dir('data/vtac_merged/PRODUCT_INFO')
            print(f"Loaded {len(products_dicts)} products from jsons")
            name_key = 'name'
            sku_key = 'default_code'
        else:
            products_dicts = Util.load_excel_columns_in_dictionary_list(excel_path)
            print(f"Loaded {len(products_dicts)} products from excel")
            name_key = 'Nombre'
            sku_key = 'Referencia interna'

        for line in products_dicts:
            product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', str(line[sku_key]))])

            if product_ids:
                product = cls.PRODUCT_MODEL.browse(product_ids[0])
                if product.name != line[name_key]:
                    cls.PRODUCT_MODEL.write(product.id, {'name': line[name_key]})
                    cls.logger.info(f"{product.default_code}: UPDATED NAME TO {line[name_key]}")
                else:
                    cls.logger.info(f"{product.default_code}: NAME ALREADY CORRECT")

    @classmethod
    def generate_missing_products_excel(cls, products, eu_stock):
        missing_products = []
        skus_to_skip = Util.load_json('data/common/json/SKUS_TO_SKIP.json')["skus"]
        skus_in_odoo = [product.default_code for product in products]

        for row in eu_stock:
            if (str(row['SKU']) not in skus_to_skip
                    and str(row['SKU']) not in skus_in_odoo
                    and (
                            (not pd.isna(row['AVAILABLE']) and int(row['AVAILABLE']) > 0 )
                            or not pd.isna(row['UNDELIVERED ORDER'])
                    )):
                missing_products.append(row)

        pd.DataFrame(missing_products).to_excel('data/common/excel/products_in_eustock_not_odoo16_and_qty_greater_than_0.xlsx')
        cls.logger.info(f"GENERATED EXCEL WITH {len(missing_products)} PRODUCTS MISSING FROM 16")

    @classmethod
    def get_buyled_stock(cls, sku):
        data = Util.load_data_in_dir('data/buyled_stocks')

        for product_stock in data:
            if product_stock['SKU'] == sku:
                cls.logger.info(f"FOUND {sku} IN B-LED STOCK")
                return {'ita': product_stock['stock_ita'], 'bled': product_stock['stock_buyled']}

        return {'ita': 0, 'bled': 0}

    @classmethod
    def get_uk_stock(cls, sku):
        data = Util.load_data_in_dir('data/vtac_uk/PRODUCT_INFO')

        for product_stock in data:
            if product_stock['default_code'] == sku:
                cls.logger.info(f"FOUND {sku} IN UK STOCK")

                # TEMP remove after a uk re-scrape
                if 'transit' not in product_stock:
                    product_stock['transit'] = 0
                if 'almacen2_custom' not in product_stock:
                    product_stock['almacen2_custom'] = 0

                return {'uk': product_stock['almacen2_custom'], 'transit': product_stock['transit']}

        return {'uk': 0, 'transit': 0}
