from dotenv import load_dotenv
from pyprojroot import here

import yaml

class LoadToolsConfig:

    def __init__(self) -> None:
        load_dotenv()

        with open(here("configs/tools_config.yml")) as cfg:
            app_config = yaml.load(cfg, Loader=yaml.FullLoader)

        # Primary Agent
        self.supervisor_agent_name = app_config["supervisor_agent"]["name"]
        self.supervisor_agent_llm = app_config["supervisor_agent"]["llm"]
        self.supervisor_agent_llm_temperature = app_config["supervisor_agent"]["llm_temperature"]

        # Spark SQL Agent config
        self.spark_sql_agent_name = app_config["spark_sql_agent"]["name"]
        self.spark_sql_agent_llm = app_config["spark_sql_agent"]["llm"]
        self.spark_sql_agent_llm_temperature = app_config["spark_sql_agent"]["llm_temperature"]
        self.spark_sql_agent_step_timeout = app_config["spark_sql_agent"]["step_timeout"]

        # RAG Agent
        self.rag_agent_name = app_config["rag_agent"]["name"]
        self.rag_agent_embedding = app_config["rag_agent"]["embedding"]
        self.rag_agent_vs_table = app_config["rag_agent"]["vs_table"]
        self.rag_agent_vs_query = app_config["rag_agent"]["vs_query"]

        # Internet Search config
        self.tavily_search_max_results = int(app_config["tavily_search_api"]["max_search_results"])

        # LangGraph configs
        self.thread_id = str(app_config["graph_configs"]["thread_id"])

