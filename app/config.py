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
        Initialize the Config instance and populate its configuration mapping.
        
        Creates an empty dictionary at self.config, populates it with values read from the application's Pydantic settings, and then overlays any values found in the optional retention JSON file (default: "memos.as/config/retention.json").
        """
        self.config = {}
        self.load_config_from_env()
        self.load_config_from_file()

    def load_config_from_env(self):
        """
        Populate the instance config dictionary with TTL and namespace values sourced from the application's Pydantic settings.
        
        Sets the following keys on self.config: MEMORY_QUERY_TTL, EMBEDDING_TTL, WORKING_MEMORY_TTL, TOOL_CACHE_TTL, LLM_RESPONSE_TTL, MEMORY_EXPIRATION_INTERVAL_SECONDS, and APEX_NAMESPACE.
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
        Load configuration from a JSON file and merge its contents into this instance's config.
        
        If the file at `filepath` exists, parse it as JSON and update `self.config` with the resulting mapping; if the file does not exist, no changes are made. Any file I/O or JSON parsing errors will propagate to the caller.
        
        Parameters:
            filepath (str): Path to the JSON configuration file (default: "memos.as/config/retention.json").
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