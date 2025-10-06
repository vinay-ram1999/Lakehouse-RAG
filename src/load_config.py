from pyprojroot import here

import yaml

class LoadToolsConfig:

    def __init__(self) -> None:
        with open(here("configs/tools_config.yml")) as cfg:
            app_config = yaml.load(cfg, Loader=yaml.FullLoader)

        # Primary agent
        self.primary_agent_llm = app_config["primary_agent"]["llm"]
        self.primary_agent_llm_temperature = app_config["primary_agent"]["llm_temperature"]

        # Internet Search config
        self.tavily_search_max_results = int(app_config["tavily_search_api"]["max_search_results"])

        # Graph configs
        self.thread_id = str(app_config["graph_configs"]["thread_id"])

        # Langsmith memory config
        self.memory_dir = here(app_config["langsmith_memory"]["directory"])

