import logging

from utils.util import Util


class Loggers:
    @staticmethod
    def setup_logger(target_file, name):
        # Create or get a logger
        logger = logging.getLogger(name)

        # Set log level
        logger.setLevel(logging.DEBUG)

        # Create a file handler
        fh = logging.FileHandler(target_file)
        fh.setLevel(logging.DEBUG)

        # Create a console handler and set its logging level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Create a formatter and set the formatter for the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        # Add the handlers to logger
        logger.addHandler(fh)
        logger.addHandler(console_handler)

        return logger

    @classmethod
    def setup_vtac_logger(cls, country):
        # Creación del logger
        logger_path_template = 'logs/{}/{}_{}.log'
        logger_path = logger_path_template.format(country, country, Util.DATETIME)
        print(f'LOGGER CREATED: {logger_path}')
        return cls.setup_logger(logger_path, f'vtac_{country}')

    @classmethod
    def setup_merge_logger(cls):
        # Creación del logger
        merger_log_file_path = 'logs/datamerger/merge_{}.log'
        logger_path = merger_log_file_path.format(Util.DATETIME)
        print(f'LOGGER CREATED: {logger_path}')
        return cls.setup_logger(logger_path, 'data_merger')

    @classmethod
    def setup_odoo_import_logger(cls):
        logger_path_template = 'logs/odooimport/import_{}.log'
        logger_path = logger_path_template.format(Util.DATETIME)
        print(f'LOGGER CREATED: {logger_path}')
        return cls.setup_logger(logger_path, 'odoo_import')
