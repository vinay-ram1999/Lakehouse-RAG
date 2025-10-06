from dotenv import load_dotenv
from pyprojroot import here

import yaml

class LoadToolsConfig:

    def __init__(self) -> None:
        load_dotenv()

        with open(here("configs/tools_config.yml")) as cfg:
            app_config = yaml.load(cfg, Loader=yaml.FullLoader)

        # Primary Agent
        self.primary_agent_llm = app_config["primary_agent"]["llm"]
        self.primary_agent_llm_temperature = app_config["primary_agent"]["llm_temperature"]

        # Internet Search config
        self.tavily_search_max_results = int(app_config["tavily_search_api"]["max_search_results"])

        # Spark SQL Agent config
        self.spqrk_sql_agent_llm = app_config["spark_sql_agent"]["llm"]
        self.spqrk_sql_agent_llm_temperature = app_config["spark_sql_agent"]["llm_temperature"]
        self.spqrk_sql_agent_step_timeout = app_config["spark_sql_agent"]["step_timeout"]

        # LangGraph configs
        self.thread_id = str(app_config["graph_configs"]["thread_id"])

        # Langsmith memory config
        self.memory_dir = here(app_config["langsmith_memory"]["directory"])

