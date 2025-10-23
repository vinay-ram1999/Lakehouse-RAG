from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent, ToolNode
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama.chat_models import ChatOllama
from langgraph_supervisor import create_supervisor
from langgraph.errors import GraphRecursionError
from langchain_core.messages import AnyMessage
from langchain_groq import ChatGroq

import os

from .backend import State, BasicToolNode, route_tools, plot_agent_schema
from ..prompts.spark_sql import SYSTEM_PROMPT as SPARK_SQL_SYS_PROMPT
from ..prompts.supervisor import SYSTEM_PROMPT as SUPERVISOR_PROMPT
from .tools.rag import load_supabase_retriever_tool, route_question
from .tools.spark_sql import get_spark_sql_tools, SparkSQLResponse
from .tools.tavily_search import load_tavily_search_tool
from ..load_config import LoadToolsConfig

TOOLS_CFG = LoadToolsConfig()

CATALOG = os.environ.get("UC_CATALOG_NAME", "tpch")
SCHEMA = os.environ.get("UC_SCHEMA_NAME", "bronze")


def build_graph() -> CompiledStateGraph:
    """Builds a graph with multi-agent supervisor architecture"""

    spark_sql_agent_llm = ChatGroq(model=TOOLS_CFG.spark_sql_agent_llm, temperature=TOOLS_CFG.spark_sql_agent_llm_temperature)
    # spark_sql_agent_llm = ChatOllama(model="gpt-oss:120b-cloud", temperature=TOOLS_CFG.spark_sql_agent_llm_temperature) #NOTE local dev only
    spark_sql_tools = get_spark_sql_tools(spark_sql_agent_llm) + [SparkSQLResponse]

    spark_sql_agent_prompt = ChatPromptTemplate([
            ("system", SPARK_SQL_SYS_PROMPT.format(**{"CATALOG_NAME": CATALOG, "SCHEMA_NAME": SCHEMA})),
            ("placeholder", "{messages}"),
            ("placeholder", "{agent_scratchpad}"),
    ])

    spark_sql_agent = create_react_agent(model=spark_sql_agent_llm, tools=spark_sql_tools, prompt=spark_sql_agent_prompt, name=TOOLS_CFG.spark_sql_agent_name)

    plot_agent_schema(spark_sql_agent, "spark_sql_agent")

    supervisor_llm = ChatGroq(model=TOOLS_CFG.supervisor_agent_llm, temperature=TOOLS_CFG.supervisor_agent_llm_temperature)
    # supervisor_llm = ChatOllama(model="gpt-oss:120b-cloud", temperature=TOOLS_CFG.supervisor_agent_llm_temperature) #NOTE local dev only
    search_tool = load_tavily_search_tool(TOOLS_CFG.tavily_search_max_results)
    retriever_tool = load_supabase_retriever_tool()
    
    supervisor = create_supervisor(
        model=supervisor_llm,
        agents=[spark_sql_agent],
        tools=[search_tool, retriever_tool],
        prompt=SUPERVISOR_PROMPT,
        # add_handoff_back_messages=True,
        add_handoff_back_messages=False,
        add_handoff_messages=False,
        output_mode="full_history",
        parallel_tool_calls=False,
        supervisor_name=TOOLS_CFG.supervisor_agent_name,
    )

    # supervisor.add_node("tavily_search", ToolNode([search_tool]))
    # supervisor.add_node("supabase_retriever", ToolNode([retriever_tool]))
    # supervisor.add_conditional_edges(
    #     TOOLS_CFG.supervisor_agent_name,
    #     route_question,
    #     {
    #         "web_search": "tavily_search",
    #         "retriever": "supabase_retriever"
    #     },
    # )

    # supervisor.add_edge("tavily_search", TOOLS_CFG.supervisor_agent_name)

    memory = MemorySaver()
    graph = supervisor.compile(checkpointer=memory)
    plot_agent_schema(graph, "supervisor_agent")
    return graph
