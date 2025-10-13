"""
Configuration management for memos.as
DEPRECATED: This module is maintained for backward compatibility.
Use app.settings.settings instead for new code.
"""
import os
import json
import logging
from .settings import settings as _settings


class Config:
    """Legacy configuration class - wraps Pydantic settings for backward compatibility."""
    
    def __init__(self):
        """
        Initialize a Config instance and populate its configuration store.
        
        Creates an internal dictionary for configuration values, loads defaults from the centralized settings source, and merges any overrides from the optional retention.json file if present.
        """
        self.config = {}
        self.load_config_from_env()
        self.load_config_from_file()

    def load_config_from_env(self):
        """
        Populate the instance's config dictionary with retention and namespace values from the centralized Pydantic settings.
        
        This sets the following keys in self.config: "MEMORY_QUERY_TTL", "EMBEDDING_TTL", "WORKING_MEMORY_TTL", "TOOL_CACHE_TTL", "LLM_RESPONSE_TTL", "MEMORY_EXPIRATION_INTERVAL_SECONDS", and "APEX_NAMESPACE", using the corresponding attributes from the module-level `_settings` object.
        """
        self.config["MEMORY_QUERY_TTL"] = _settings.memory_query_ttl
        self.config["EMBEDDING_TTL"] = _settings.embedding_ttl
        self.config["WORKING_MEMORY_TTL"] = _settings.working_memory_ttl
        self.config["TOOL_CACHE_TTL"] = _settings.tool_cache_ttl
        self.config["LLM_RESPONSE_TTL"] = _settings.llm_response_ttl
        self.config["MEMORY_EXPIRATION_INTERVAL_SECONDS"] = _settings.memory_expiration_interval_seconds
        self.config["APEX_NAMESPACE"] = _settings.apex_namespace

    def load_config_from_file(self, filepath="memos.as/config/retention.json"):
        """
        Load configuration from a JSON file and merge its keys into the instance's config.
        
        Parameters:
            filepath (str): Path to a JSON file containing configuration keys. If the file exists, its parsed entries are merged into self.config, overwriting any existing keys with the same names. The default path is "memos.as/config/retention.json".
        """
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