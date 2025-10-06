from langchain_community.agent_toolkits import SparkSQLToolkit
from langchain_community.utilities.spark_sql import SparkSQL
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError
from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from pyspark.sql import SparkSession
from langchain_groq import ChatGroq

from typing import List
import os

from ...prompts.spark_sql import SYSTEM_PROMPT, USER_PROMPT
from ...utils.app_utils import get_spark_session_sync
from ...load_config import LoadToolsConfig

TOOLS_CFG = LoadToolsConfig()

CATALOG = os.environ.get("UC_CATALOG_NAME", "tpch")
SCHEMA = os.environ.get("UC_SCHEMA_NAME", "bronze")

class SparkSQLAgentTool:
    """
    A tool for interacting with a Spark SQL schema using an LLM (Language Model) to generate and execute SQL queries.
    """

    def __init__(self, llm: str, llm_temerature: float, spark: SparkSession, catalog_name: str = CATALOG, schema_name: str = SCHEMA, **kwargs) -> None:
        """
        Initializes the SparkSQLAgentTool with the necessary configurations.

        Args:
            llm (str): The name of the language model to be used for generating and interpreting SQL queries.
            spark (SparkSession): The Databricks spark session object to execute Spark SQL queties.
            llm_temerature (float): The temperature setting for the language model, controlling response randomness.
        """
        llm_model = ChatGroq(model=llm, temperature=llm_temerature)
        spark_sql = SparkSQL(spark_session=spark, catalog=catalog_name, schema=schema_name)
        spark_sql_toolkit = SparkSQLToolkit(db=spark_sql, llm=llm_model)

        prompt = ChatPromptTemplate([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
            # Placeholders fill up a **list** of messages
            ("placeholder", "{messages}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        tools = spark_sql_toolkit.get_tools()
        self.executor = create_react_agent(model=llm_model, tools=tools, prompt=prompt)
        # self.executor.step_timeout = kwargs.get("step_timeout", 5)


@tool
def query_spark_sql_tool(query: str) -> str:
    """Use this tool to execute queries on Spark SQL. Input should be a search query."""
    spark: SparkSession = get_spark_session_sync()
    agent = SparkSQLAgentTool(
        llm = TOOLS_CFG.spqrk_sql_agent_llm,
        spark = spark,
        llm_temerature = TOOLS_CFG.spqrk_sql_agent_llm_temperature,
        **{"step_timeout": TOOLS_CFG.spqrk_sql_agent_step_timeout}
    )
    # messages = agent.executor.invoke({"input": query})
    messages = []
    response = agent.executor.astream({"messages": [("input", query)]}, stream_mode="updates")
    return response
