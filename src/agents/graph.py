from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START
from langchain_groq import ChatGroq

from .backend import State, BasicToolNode, route_tools, plot_agent_schema
from .tools import load_tavily_search_tool, get_spark_sql_tools
from ..prompts.spark_sql import SYSTEM_PROMPT as SPARK_SQL_SYS_PROMPT
from ..load_config import LoadToolsConfig

TOOLS_CFG = LoadToolsConfig()

def build_graph():
    """Builds a graph with multi-agent supervisor architecture"""

    spark_sql_agent_llm = ChatGroq(model=TOOLS_CFG.spark_sql_agent_llm, temperature=TOOLS_CFG.spark_sql_agent_llm_temperature)
    spark_sql_tools = get_spark_sql_tools(spark_sql_agent_llm)

    spark_sql_agent_prompt = ChatPromptTemplate([
            ("system", SPARK_SQL_SYS_PROMPT),
            ("placeholder", "{messages}"),
            ("placeholder", "{agent_scratchpad}"),
    ])

    spark_sql_agent = create_react_agent(model=spark_sql_agent_llm, tools=spark_sql_tools, prompt=spark_sql_agent_prompt, name=TOOLS_CFG.spark_sql_agent_name)

    supervisor_llm = ChatGroq(model=TOOLS_CFG.supervisor_agent_llm, temperature=TOOLS_CFG.supervisor_agent_llm_temperature)
    search_tool = load_tavily_search_tool(TOOLS_CFG.tavily_search_max_results)
    
    supervisor = create_supervisor(
        model=supervisor_llm,
        agents=[spark_sql_agent],
        tools=[search_tool],
        prompt=(
            "You are a supervisor managing one agent:\n"
            "- a spark sql agent. Assign Spark SQL query related tasks to this agent\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself."
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
        parallel_tool_calls=False,
        supervisor_name=TOOLS_CFG.supervisor_agent_name,
    )

    memory = MemorySaver()
    graph = supervisor.compile(checkpointer=memory)
    plot_agent_schema(graph)
    return graph
