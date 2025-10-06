from dotenv import load_dotenv
import os
load_dotenv()

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

from langchain.chat_models import init_chat_model
llm_model = init_chat_model("llama-3.3-70b-versatile", model_provider="groq")

from pyspark.sql.connect.client.core import SparkConnectGrpcException
from databricks.connect import DatabricksSession

from langchain_community.agent_toolkits import SparkSQLToolkit, create_spark_sql_agent
from langchain_community.utilities.spark_sql import SparkSQL

try:
    spark = DatabricksSession.builder.getOrCreate()
    spark_sql = SparkSQL(spark_session=spark)
    toolkit = SparkSQLToolkit(db=spark_sql, llm=llm_model)
except SparkConnectGrpcException:
    spark = DatabricksSession.builder.create()
    spark_sql = SparkSQL(spark_session=spark)
    toolkit = SparkSQLToolkit(db=spark_sql, llm=llm_model)

from langchain_core.tools import tool

from typing import Union
import json

@tool
def get_all_schemas_info(catalog_name: str) -> str:
    """Use this tool to find all available schemas present in the given catalog."""
    schemas = []
    workspace_client = w
    for schema in workspace_client.schemas.list(catalog_name=catalog_name):
        schema_info = json.dumps({
            "name": schema.name,
            "full_name": schema.full_name,
            "description": schema.comment
        })
        schemas.append(schema_info) if schema.name != "information_schema" else None
    schemas.append("\n")
    return "\n".join(schemas)

@tool()
def get_all_tables_info(catalog_name: str, schema_name: Union[str, list] | None = None) -> str:
    """Use this tool to find the information of all available tables (including description and columns information) present in the given catalog and schema"""
    tables = []
    workspace_client = w

    if schema_name is None:
        return f"The user has not specified the 'schema_name'. Collect all available schemas and recall this tool with the list of schemas as question"
    
    if isinstance(schema_name, str):
        for table in workspace_client.tables.list(catalog_name=catalog_name, schema_name=schema_name):
            table_constraints = w.tables.get(full_name=table.full_name).table_constraints #BUG table.table_constraints has some bug and is returning None
            table_info = json.dumps({
                "name": table.name,
                "full_name": table.full_name,
                "type": table.table_type.name,
                "description": table.comment,
                "columns": [table.columns[0].as_dict()] if table.columns else None,
                "constraints": table_constraints[0].as_dict() if table_constraints else None,
                "view_definition": table.view_definition,
                "view_dependencies": table.view_dependencies.as_dict() if table.view_dependencies else None
            })
            tables.append(table_info)
    else:
        for schema in schema_name:
            for table in workspace_client.tables.list(catalog_name=catalog_name, schema_name=schema):
                table_constraints = w.tables.get(full_name=table.full_name).table_constraints #BUG table.table_constraints has some bug and is returning None
                table_info = json.dumps({
                    "name": table.name,
                    "full_name": table.full_name,
                    "type": table.table_type.name,
                    "description": table.comment,
                    "columns": [table.columns[0].as_dict()] if table.columns else None,
                    "constraints": table_constraints[0].as_dict() if table_constraints else None,
                    "view_definition": table.view_definition,
                    "view_dependencies": table.view_dependencies.as_dict() if table.view_dependencies else None
                })
                tables.append(table_info)
    tables.append("\n")
    return "\n".join(tables)

from langchain_community.tools.spark_sql.tool import QueryCheckerTool, QuerySparkSQLTool
from langchain_community.tools import BaseTool

checker_prompt = """
Use this tool to double check if your query is correct before executing it.
Always use this tool before executing a query with 'query_executor_tool'!

- Minimize data shuffle and use efficient join strategies 
- Make sure the table/view name follows three-level namespace ('<catalog>.<schema>.<table>')

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.
"""

query_prompt = """
Input to this tool is a detailed and correct SQL query, output is a result from the Spark SQL.
Always consider to use tools like 'get_all_schemas_info', 'get_all_tables_info', and 'query_checker_tool', 

If the query is not correct, an error message will be returned.
If an error is returned, always revert back to other tools to fix the error and rewrite the query, check the query, and then try again.
If the error is not resolved, return 'Unable to generate the result. Provide more context to generate accurate results'!
"""

query_checker_tool: BaseTool = QueryCheckerTool(llm=llm_model, db=spark_sql, description=checker_prompt, name="query_checker_tool").as_tool()
query_executor_tool: BaseTool = QuerySparkSQLTool(db=spark_sql, description=query_prompt, name="query_executor_tool").as_tool()

from pydantic import BaseModel, Field

class SqparkSQLAgentOutput(BaseModel):
    query: str = Field(description="The actual query executed to generate the result.")
    result: str = Field(description="The output generated after executing the Spark SQL query (if the execution failed this will be the error message returned).")
    summary: str = Field(description="Summarize the 'result' in natural language")

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate

system_prompt = SystemMessagePromptTemplate.from_template(template="""
You are a Databricks Lakehouse assistant for exploring workspace artifacts via Unity Catalog and Spark SQL.

Rules & constraints:
- Unity Catalog uses a three-level namespace: <catalog>.<schema>.<table>. Always reference tables with the full three-level name.
- You are only allowed to access the '{catalog_name}' catalog. If the user requests or attempts to access any other catalog, return exactly: "Unauthorized to access, contact the Admin".
- Do not fabricate metadata, schema, or query results. If required information is missing, state what is missing and which tool call would obtain it.

Mandatory tool usage:
- Before composing any Spark SQL query:
  1. If the user provided a schema name: call get_all_tables_info with that schema.
  2. If the user did NOT provide a schema: call get_all_schemas_info with the default catalog '{catalog_name}', then call get_all_tables_info with the list of schemas returned.
- Always run query_checker_tool to validate and (if required) rewrite the SQL before executing with query_executor_tool.
- If a tool returns an error, include the tool error in the agent scratchpad and attempt corrective actions. If you cannot resolve the error, return: "Unable to generate the result. Provide more context to generate accurate results".

SQL best-practices:
- Use fully-qualified identifiers (`<catalog_name>.<schema_name>.<table_name>`).
- Prefer targeted projections and predicates (avoid `SELECT *` on large tables).
- When aggregating large datasets, prefer `COUNT(...)`, `LIMIT`, or other reducing strategies to minimize shuffle.
- Quote identifiers where necessary.

Behavioral rules:
- Keep final output strictly to the agent's required final message (no extra explanation unless explicitly requested).
- If asked for metadata, return only data that was retrieved from the tools.

Help the user by using available tools and returning concise, accurate results.
"""
)

human_prompt = HumanMessagePromptTemplate.from_template(template="""
Assist the user with the following question:
---
{question}
---
IMPORTANT: Only output the required final message for downstream consumption (no extra commentary). Use the mandated tools and validation steps described in the system prompt. If you execute SQL, ensure it has been validated by 'query_checker_tool' before calling 'query_executor_tool'.
"""
)

# Include MessagesPlaceholder entries for the runtime-injected fields.
# Some runtimes use 'messages', some 'remaining_steps' — include both to be safe.
prompt = ChatPromptTemplate.from_messages([
        system_prompt,
        MessagesPlaceholder(variable_name="messages"),
        human_prompt,
        MessagesPlaceholder(variable_name="remaining_steps"),
])

# prompt = ChatPromptTemplate.from_messages([
#     system_prompt, # MessagesPlaceholder(variable_name="chat_history"),
#     human_prompt,
#     ("placeholder", "{agent_scratchpad}"),
# ])

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

tools = [get_all_schemas_info, get_all_tables_info, query_checker_tool, query_executor_tool]

memory = MemorySaver()
react_agent = create_react_agent(model=llm_model, tools=tools, prompt=prompt, checkpointer=memory)

config = {"configurable": {"thread_id": "abc123"}}
question = "Count the total number of customers in bronze schema"

for step in react_agent.stream({"catalog_name": "tpch", "question": question}, config=config, stream_mode="values"):
    step["messages"][-1].pretty_print()



