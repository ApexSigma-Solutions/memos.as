import os
import json
import logging


class Config:
    def __init__(self):
        self.config = {}
        self.load_config_from_env()
        self.load_config_from_file()

    def load_config_from_env(self):
        self.config["MEMORY_QUERY_TTL"] = int(os.environ.get("MEMORY_QUERY_TTL", 1800))
        self.config["EMBEDDING_TTL"] = int(os.environ.get("EMBEDDING_TTL", 3600))
        self.config["WORKING_MEMORY_TTL"] = int(
            os.environ.get("WORKING_MEMORY_TTL", 300)
        )
        self.config["TOOL_CACHE_TTL"] = int(os.environ.get("TOOL_CACHE_TTL", 7200))
        self.config["LLM_RESPONSE_TTL"] = int(os.environ.get("LLM_RESPONSE_TTL", 14400))
        self.config["MEMORY_EXPIRATION_INTERVAL_SECONDS"] = int(
            os.environ.get("MEMORY_EXPIRATION_INTERVAL_SECONDS", 3600)
        )
        self.config["APEX_NAMESPACE"] = os.environ.get("APEX_NAMESPACE", "apex:memos")

    def load_config_from_file(self, filepath="memos.as/config/retention.json"):
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                file_config = json.load(f)
                self.config.update(file_config)

    def get(self, key):
        return self.config.get(key)

    def get_ttl(self, key):
        return self.get(key)

    def get_logger(self, name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger


_config = Config()


def get_config():
    return _config
