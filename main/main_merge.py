from utils.data_merger import DataMerger
from utils.loggers import Loggers

# Merge uk + eso + ita
IF_MERGE = True
IF_OMIT_MEDIA = False
IF_ONLY_NEW_PRODUCTS = False

DataMerger.logger = Loggers.setup_merge_logger()

# DATA MERGING
if IF_MERGE:
    DataMerger.logger.info('BEGINNING DATA MERGING')
    data, media = DataMerger.load_all(IF_ONLY_NEW_PRODUCTS, IF_OMIT_MEDIA).merge_data(IF_OMIT_MEDIA)
    DataMerger.extract_merged_data(data, media, IF_ONLY_NEW_PRODUCTS)
    DataMerger.logger.info('FINISHED DATA MERGING')
