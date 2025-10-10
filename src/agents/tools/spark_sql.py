from langchain_core.language_models.base import BaseLanguageModel
from langchain_community.utilities.spark_sql import SparkSQL
from langchain_community.tools.spark_sql.tool import (
    QuerySparkSQLTool,
    InfoSparkSQLTool,
    ListSparkSQLTool,
    QueryCheckerTool,
)
from langchain_core.tools import BaseTool

from dotenv import load_dotenv

from typing import List
import os

from ...utils.app_utils import get_spark_session_sync

load_dotenv()

CATALOG = os.environ.get("UC_CATALOG_NAME", "tpch")
SCHEMA = os.environ.get("UC_SCHEMA_NAME", "bronze")

class DynamicQuerySparkSQLTool(QuerySparkSQLTool):
    """Dynamic variant of QuerySparkSQLTool with auto-refreshing SparkSession."""

    def _run(self, query: str, **kwargs):
        _spark = get_spark_session_sync()
        self.db = SparkSQL(spark_session=_spark, catalog=CATALOG, schema=SCHEMA)
        return super()._run(query, **kwargs)


class DynamicInfoSparkSQLTool(InfoSparkSQLTool):
    """Dynamic variant of InfoSparkSQLTool."""

    def _run(self, table_names: str, **kwargs):
        _spark = get_spark_session_sync()
        self.db = SparkSQL(spark_session=_spark, catalog=CATALOG, schema=SCHEMA)
        return super()._run(table_names, **kwargs)


class DynamicListSparkSQLTool(ListSparkSQLTool):
    """Dynamic variant of ListSparkSQLTool."""

    def _run(self, tool_input: str = "", **kwargs):
        _spark = get_spark_session_sync()
        self.db = SparkSQL(spark_session=_spark, catalog=CATALOG, schema=SCHEMA)
        return super()._run(tool_input, **kwargs)


class DynamicQueryCheckerTool(QueryCheckerTool):
    """Dynamic variant of QueryCheckerTool."""

    def _run(self, query: str, **kwargs):
        _spark = get_spark_session_sync()
        self.db = SparkSQL(spark_session=_spark, catalog=CATALOG, schema=SCHEMA)
        return super()._run(query, **kwargs)

    async def _arun(self, query: str, **kwargs):
        _spark = get_spark_session_sync()
        self.db = SparkSQL(spark_session=_spark, catalog=CATALOG, schema=SCHEMA)
        return await super()._arun(query, **kwargs)


def get_spark_sql_tools(llm_model: BaseLanguageModel) -> List[BaseTool]:
    """Initiate all Dynamic Spark SQL tools and return them in a list"""
    spark = get_spark_session_sync()
    spark_sql = SparkSQL(spark_session=spark, catalog=CATALOG, schema=SCHEMA)

    query_spark_tool = DynamicQuerySparkSQLTool(db=spark_sql)
    info_spark_tool = DynamicInfoSparkSQLTool(db=spark_sql)
    list_spark_tool = DynamicListSparkSQLTool(db=spark_sql)
    check_spark_tool = DynamicQueryCheckerTool(db=spark_sql, llm=llm_model)
    
    return [query_spark_tool, info_spark_tool, list_spark_tool, check_spark_tool]
