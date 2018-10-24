###############################################################################
#
# PRE-PROCESSED LIBRARY - EDITS WILL BE CLOBBERED BY MAVEN BUILD
#
# This file is in the LIBRARY pre-processed state with template available by the
# same package and file name under the modules src/main/template directory.
#
# If editing as a SCRIPT or LIBRARY, all changes must be merged to the TEMPLATE,
# else they will be locally clobbered by the maven build. Am automated merge
# process (revealing template diffs) is provided by the bootstrap script.
#
# When editing as a TEMPLATE directly (as indicated by the presence of the
# TEMPLATE.PRE-PROCESSOR.RAW_TEMPLATE tag at the top of this file), care should
# be taken to ensure the maven-resources-plugin generate-sources filtering of the
# TEMPLATE.PRE-PROCESSOR tags, which comment and or uncomment blocks of the
# template, leave the file in a consistent state, as a script or library,
# post filtering.
#
# The SCRIPT can be tested from within CDSW, the LIBRARY as part of  the maven
# test phase.
#
# This is an example pipeline that shows the scaffolding necessary to query the
# core dataset, filtering, re-sampling and writing out a subset of the data,
# specifically temperature
#
###############################################################################

import re
import sys
import tempfile
import time

import pandas as pd
from pyspark.sql import SparkSession

# Add working directory to the system path# IGNORE SCRIPT BOILERPLATE #sys.path.insert(0, 'asystem-amodel/src/main/script/python')

from repo_util import paths
from script_util import qualify

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def pipeline():
    remote_data_path = sys.argv[1] if len(sys.argv) > 1 else "s3a://asystem-astore"

    print("Pipeline starting on [{}]".format(remote_data_path))
    time_start = int(round(time.time()))
    spark = SparkSession.builder.appName("asystem-amodel-dataset").getOrCreate()
    print("Session created ...")

    # datasets = []
    # for path in [os.path.join(remote_data_path, str(i),
    #                           "asystem/astore/processed/canonical/parquet/dict/snappy"
    #                           ) for i in range(10)]:
    #     try:
    #         path_uri = qualify(path)
    #         datasets.append(spark.read.parquet(path_uri))
    #         print("Cached partitions [{}]".format(path_uri))
    #     except AnalysisException:
    #         continue
    # dataset = reduce(lambda x, y: x.union(y), datasets)

    # from boto.s3.connection import S3Connection
    # s3_connection = S3Connection()
    # s3_bucket = s3_connection.get_bucket('asystem-astore')
    # prefix = '/asystem/astore/processed/canonical/parquet/dict/snappy/'
    # partitions = ['/astore_metric=temperature/']
    # suffix = 'parquet'
    # paths = []
    # for i in range(10):
    #     for path in list(s3_bucket.list(prefix=str(i) + prefix)):
    #         if path.key.endswith(suffix) and any(partition in path.key for partition in partitions):
    #             paths.append(os.path.join(remote_data_path, path.key))
    # dataset = spark.read.parquet(*paths)

    # paths = ['s3a://asystem-astore/[0-9]/asystem/astore/processed/canonical/parquet/dict/snappy/' +
    #          '*/*/*/*/astore_metric=temperature/*.snappy.parquet']
    # dataset = spark.read.parquet(*paths)

    dataset = spark.read.parquet(
        *paths(qualify(remote_data_path + "/[0-9]/asystem/astore/processed/canonical/parquet/dict/snappy"),
               "/*/*/*/*/astore_metric=temperature", "/*.snappy.parquet"))

    print("Listing finished ...")
    dataset.createOrReplaceTempView('dataset')

    # dataset = spark.sql("""
    #     SELECT
    #       bin_timestamp AS timestamp,
    #       data_metric AS metric,
    #       data_temporal AS temporal,
    #       data_value / data_scale AS temperature
    #     FROM dataset
    #     WHERE
    #       astore_metric='temperature' AND
    #       data_temporal='current' AND
    #       data_type='point' AND
    #       data_version=2 AND
    #       data_metric NOT LIKE '%forecast%' AND
    #       data_metric NOT LIKE '%parents' AND
    #       data_metric NOT LIKE '%shed' AND
    #       data_metric NOT LIKE '%roof'
    #     ORDER BY timestamp
    # """)

    dataset = spark.sql("""
        SELECT
          bin_timestamp AS timestamp,
          data_metric AS metric,
          data_temporal AS temporal,
          data_value / data_scale AS temperature
        FROM dataset
        WHERE
          data_temporal='current' AND
          data_type='point' AND
          data_version=2 AND
          data_metric NOT LIKE '%forecast%' AND
          data_metric NOT LIKE '%parents' AND
          data_metric NOT LIKE '%shed' AND
          data_metric NOT LIKE '%roof'
        ORDER BY timestamp
    """)

    dataframe = dataset.toPandas()
    print("Dataset collected ...")
    dataframe = dataframe.pivot_table(
        values='temperature', index='timestamp', columns='metric')
    dataframe = dataframe.set_index(pd.to_datetime(dataframe.index, unit='s')
                                    .tz_localize('UTC').tz_convert('Australia/Perth'))
    dataframe = dataframe.loc[(dataframe.index.strftime('%Y-%m-%d') >= '2018-07-19')]
    dataframe = dataframe.fillna(method='bfill')
    dataframe = dataframe.fillna(method='ffill')
    dataframe = dataframe.resample('300S').mean()
    dataframe = dataframe.fillna(method='bfill')
    dataframe = dataframe.fillna(method='ffill')
    dataframe = dataframe.round(1)
    dataframe = dataframe.loc[(dataframe < 50).all(axis=1), :]
    dataframe = dataframe.loc[(dataframe > -10).all(axis=1), :]
    dataframe.columns = dataframe.columns.map(
        lambda name: re.compile('.*__.*__(.*)').sub('\\1', name))
    print("Dataset compiled ...")
    print("Training data:\n{}\n\n".format(dataframe.describe()))
    output = tempfile.NamedTemporaryFile(
        prefix='asystem-temperature-', suffix='.csv', delete=False).name
    print("Writing output to [{}]".format(output))
    dataframe.to_csv(output)
    print("Pipeline finished in [{}] s".format(int(round(time.time())) - time_start))

# Run pipeline# IGNORE SCRIPT BOILERPLATE #pipeline()

# Main function
if __name__ == "__main__":
# Run pipeline
    pipeline()
