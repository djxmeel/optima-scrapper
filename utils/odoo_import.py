import os.path
import time
from urllib.error import HTTPError

import odoorpc
import base64

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

    PRODUCT_PDF_DIRS = {'es': 'data/vtac_spain/PROD/PRODUCT_PDF',
                        'uk': 'data/vtac_uk/PROD/PRODUCT_PDF',
                        'ita': 'data/vtac_italia/PROD/PRODUCT_PDF'}

    # Fields not to create as attributes in ODOO
    NOT_ATTR_FIELDS = ('accesorios', 'videos', 'kit', 'icons', 'imgs', 'Ean', 'Código de familia', 'url', 'public_categories')

    # Invoice policy (delivery ; order)
    CURRENT_INVOICE_POLICY = 'delivery'

    # Product type (consu ; service ; product)
    PRODUCT_DETAILED_TYPE = 'product'

    # Product category (not eshop)
    PRODUCT_INTERNAL_CATEGORY = 'Productos de iluminación'

    # USE TO ONLY UPLOAD CERTAIN PRODUCTS
    PRIORITY_EXCEL_SKUS_PATH = 'data/common/excel/Productos Comprados o Vendidos VTAC.xlsx'

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

        for attr_id, value in created_attrs_values_ids.items():
            try:
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
    def assign_attribute_values(cls, product_id, product, attributes_ids_values, update_mode=False):
        attr_lines = []

        #TODO TEST
        if update_mode:
            cls.ATTRIBUTE_LINE_MODEL.unlink(cls.ATTRIBUTE_LINE_MODEL.search([('product_tmpl_id', '=', product_id)]))

        for attribute_id, value_id in attributes_ids_values.items():
            # Only check if the attribute line already exists
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
    def import_products(cls, target_dir_path, uploaded_dir_path, skip_existing, use_priority_excel=False):
        file_list = Util.get_all_files_in_directory(target_dir_path)
        counter = 0

        PRIORITY_SKUS = Util.get_priority_excel_skus('data/common/excel/Productos Comprados o Vendidos VTAC.xlsx', 'A') if use_priority_excel else []

        for file_path in sorted(file_list):
            products = Util.load_json(file_path)

            cls.logger.info(f'IMPORTING PRODUCTS OF FILE: {file_path}')

            for product in products:
                if use_priority_excel and product['default_code'] and product['default_code'] not in PRIORITY_SKUS:
                    cls.logger.info(f"SKIPPING SKU {product['default_code']} INFO BECAUSE IT IS NOT IN PRIORITY EXCEL")
                    continue

                counter += 1
                product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'])])

                attrs_to_create = {}
                temp_keys = list(product.keys())

                public_categs = product['public_categories']

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
                        cls.logger.info(f'Product {product["default_code"]} with origin URL : {url} NOT CREATED')
                        continue

                    cls.assign_internal_category(product_id, cls.PRODUCT_INTERNAL_CATEGORY)
                    cls.assign_attribute_values(product_id, product, created_attrs_ids_values, False)
                    cls.assign_public_categories(product_id, public_categs)
                elif not skip_existing:
                    product_id = product_ids[0]

                    cls.PRODUCT_MODEL.write(product_id, product)

                    cls.logger.info(f'Updating existing product {product["default_code"]} with origin URL {url}')

                    created_attrs_ids_values = cls.create_attributes_and_values(attrs_to_create)

                    cls.assign_internal_category(product_id, cls.PRODUCT_INTERNAL_CATEGORY)
                    cls.assign_attribute_values(product_id, product, created_attrs_ids_values, True)
                    cls.assign_public_categories(product_id, public_categs)

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
    def import_pdfs(cls, start_from=0, skip_products_w_attachments=False):
        product_model = cls.PRODUCT_MODEL
        attachments_model = cls.odoo.env['ir.attachment']

        # Fetch records in batches to avoid RPCerror
        batch_size = 200
        offset = 0
        skus_in_odoo = []

        while True:
            product_ids = product_model.search([], offset=offset, limit=batch_size)
            if not product_ids:  # Exit the loop when no more records are found
                break

            products = product_model.browse(product_ids)
            skus_in_odoo.extend([p.default_code for p in products])
            print(f'FETCHING ALL PRODUCTS SKUS : {len(skus_in_odoo)}')

            offset += batch_size

        directory_list_es = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['es'])
        sku_list_es = [dirr.split('\\')[-1] for dirr in directory_list_es]

        directory_list_uk = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['uk'])
        sku_list_uk = [dirr.split('\\')[-1] for dirr in directory_list_uk]

        directory_list_ita = Util.get_nested_directories(cls.PRODUCT_PDF_DIRS['ita'])
        sku_list_ita = [dirr.split('\\')[-1] for dirr in directory_list_ita]


        while False in skus_in_odoo:
            skus_in_odoo.remove(False)

        for index, sku in enumerate(sorted(skus_in_odoo[start_from:])):
            # FIXME REMOVE after REDOING the import
            atts = attachments_model.search([('res_id', '=', product_model.search([('default_code', '=', sku)])[0])])
            attachments_model.unlink(atts)

            print(f'{index+start_from+1} / {len(skus_in_odoo[start_from:])}')
            res_id = product_model.search([('default_code', '=', sku)])[0]

            if skip_products_w_attachments:
                product_uploaded_attachments = attachments_model.search([('res_id', '=', res_id)])

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

                    attachment_name = Util.attachment_naming_replacements(attachment_name.lower())

                    attachment_name = f'{res_id}_{attachment_name}'

                    existing_attachment = attachments_model.search([('name', '=', attachment_name), ('res_id', '=', res_id)])

                    if existing_attachment:
                        cls.logger.info(f'{sku}: ATTACHMENT WITH NAME {attachment_name} ALREADY EXISTS IN ODOO')
                        continue

                    attachment_data = {
                        'name': attachment_name,
                        'datas': encoded_data,
                        'res_model': 'product.template',  # Model you want to link the attachment to (optional)
                        'res_id': res_id,  # ID of the record of the above model you want to link the attachment to (optional)
                        'type': 'binary',
                    }

                    try:
                        attachment_id = attachments_model.create(attachment_data)
                        cls.logger.info(
                            f'{sku}: ATTACHMENT WITH NAME {attachment_name} UPLOADED TO ODOO WITH ID {attachment_id}')
                    except TimeoutError:
                        cls.logger.error(f"FAILED TO UPLOAD {attachment_name} FOR PRODUCT {sku}")
                        time.sleep(10)
                        cls.import_pdfs(start_from, skip_products_w_attachments)
                    except HTTPError:
                        cls.logger.error(f"HTTP ERROR: FILE {attachment_name} POTENTIALLY TOO BIG. CONTINUING")
                        continue

    @classmethod
    def import_imgs_videos(cls, target_dir_path, uploaded_dir_path):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        for file_path in sorted(file_list):
            products = Util.load_json(file_path)

            for product in products:
                if 'imgs' in product:
                    cls.logger.info(f'{product["default_code"]}: FOUND {len(product["imgs"])} IMAGES')

                    # Search for the product template with the given sku
                    product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'].strip())])

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
                                if extra_img['img64'] not in images:
                                    name = f'{product_ids[0]}_{product["imgs"].index(extra_img)}'

                                    new_image = {
                                        'name': name,
                                        'image_1920': extra_img['img64'],
                                        'product_tmpl_id': product_ids[0]
                                    }
                                    try:
                                        # Create the new product.image record
                                        cls.MEDIA_MODEL.create(new_image)
                                        cls.logger.info(f'{product["default_code"]}: UPLOADED IMAGE with name : {name}')
                                    except RPCError:
                                        cls.logger.info(f'{product["default_code"]}: ERROR UPLOADING IMAGE with name : {name} *{RPCError}*')
                                else:
                                    cls.logger.info(f'{product["default_code"]}: Image already exists')

                            cls.logger.info(f"{product['default_code']}:FINISHED UPLOADING IMAGES")

                            videos = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0]), ('video_url', '!=', False)])
                            videos = cls.MEDIA_MODEL.browse(videos)
                            videos = [video.video_url for video in videos]

                            if 'videos' in product:
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
                    else:
                        cls.logger.warn(f'{product["default_code"]} : PRODUCT NOT FOUND IN ODOO')

                else:
                    cls.logger.warn(f'{product["default_code"]} HAS NO IMAGES!')

            # Moving uploaded files to separate dir to persist progress
            Util.move_file_or_directory(file_path, f'{uploaded_dir_path}/{os.path.basename(file_path)}')

        # Restoring target dir's original name
        Util.move_file_or_directory(uploaded_dir_path, target_dir_path, True)

    @classmethod
    def import_icons(cls, target_dir_path, uploaded_dir_path):
        file_list = Util.get_all_files_in_directory(target_dir_path)

        for file_path in sorted(file_list):
            products = Util.load_json(file_path)

            for product in products:
                if 'icons' in product:
                    cls.logger.info(f'{product["default_code"]} icons: {len(product["icons"])}')

                    # Search for the product template with the given sku
                    product_ids = cls.PRODUCT_MODEL.search([('default_code', '=', product['default_code'].strip())])

                    if product_ids:
                        image_ids = cls.MEDIA_MODEL.search([('product_tmpl_id', '=', product_ids[0])])

                        # Product existing icons
                        icons_elements = cls.MEDIA_MODEL.browse(image_ids)

                        icons = [icon.image_1920 for icon in icons_elements]

                        # Iterate over the products
                        for icon in product['icons']:
                            if icon not in icons:
                                name = f'{product_ids[0]}_{product["icons"].index(icon)}'
                                new_image = {
                                    'name': name,  # Replace with your image name
                                    'image_1920': icon,
                                    'product_tmpl_id': product_ids[0]
                                }

                                try:
                                    # Create the new product.image record
                                    cls.MEDIA_MODEL.create(new_image)
                                    cls.logger.info(f'{product["default_code"]}: UPLOADED ICON with name : {name}')
                                except RPCError:
                                    pass
                            else:
                                cls.logger.info('Icon already exists')
                    else:
                        cls.logger.warn('PRODUCT NOT FOUND IN ODOO')

                else:
                    cls.logger.warn(f'{product["default_code"]} HAS NO ICONS!')

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
    def import_public_categories(cls, public_categories_path):
        public_categories = Util.load_excel_columns_in_dictionary_list(public_categories_path)
        public_categories_model = cls.odoo.env['product.public.category']

        for category in public_categories:
            if public_categories_model.search([('name', '=', category["name"]), ('parent_id.name', '=', category["parent"])]):
                cls.logger.info(f'Category {category} already exists in Odoo')
                continue

            parent_id = public_categories_model.search([('name', '=', category["parent"])])

            if parent_id:
                parent_id = parent_id[0]

            public_categories_model.create({
                'name': category["name"],
                'parent_id': parent_id,
                'sequence': category["sequence"]
            })

            cls.logger.info("CREATED CATEGORY: " + category['name'])

    @classmethod
    def browse_all_products_in_batches(cls, field=None, operator=None, value=None):
        # Fetch records in batches to avoid RPCerror
        batch_size = 200
        offset = 0
        products = []

        while True:
            if not field or not operator:
                product_ids = cls.PRODUCT_MODEL.search([], offset=offset, limit=batch_size)
            else:
                product_ids = cls.PRODUCT_MODEL.search([(field, operator, value)], offset=offset, limit=batch_size)
            if not product_ids:  # Exit the loop when no more records are found
                break

            products.extend(cls.PRODUCT_MODEL.browse(product_ids))
            cls.logger.info(f"FETCHED PRODUCTS: {len(products)}")

            offset += batch_size

        return products

    @classmethod
    def import_supplier_info(cls, supplier_stock_excel_path, supplier_pricelist_excel_path, update_mode=False):
        supplier_info_model = cls.odoo.env['product.supplierinfo']
        partner_model = cls.odoo.env['res.partner']
        partner_id = partner_model.search([('name', '=', 'V-TAC Europe Ltd.')])[0]

        products = cls.browse_all_products_in_batches()
        stock_excel_dicts = Util.load_excel_columns_in_dictionary_list(supplier_stock_excel_path)
        pricelist_excel_dicts = Util.load_excel_columns_in_dictionary_list(supplier_pricelist_excel_path)

        for product in products:
            supplier_prod_name = product.name
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
                if update_mode:
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

        products = cls.browse_all_products_in_batches()

        for product in products:
            if str(product.default_code) not in skus:
                # TODO TEST
                cls.PRODUCT_MODEL.write(product.id, {'description_purchase': f'DESCATALOGADO - {product.description_purchase}', 'name': str(product.name).replace('[VSD','[VS').replace('[VS', '[VSD')})
                cls.logger.info(f"{product.default_code}: CHANGED IN-NAME REF FROM VS TO VSD")
            else:
                cls.logger.info(f"{product.default_code} SKIPPING BECAUSE IT IS IN CATALOGO")

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
            product.write({'active': False})  # This archives the product in the database
