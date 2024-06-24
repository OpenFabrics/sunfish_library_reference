# Copyright IBM Corp. 2024
# This software is available to you under a BSD 3-Clause License.
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import importlib
import logging

logger = logging.getLogger(__name__)

plugins_namespace_name = "sunfish_plugins"


def load_plugin(plugin: dict):
    module_name = f"{plugins_namespace_name}.{plugin['module_name']}"
    logger.info(f"Loading plugin {module_name}...")
    plugin_module = importlib.import_module(module_name)
    logger.info("Plugin loaded")
    return getattr(plugin_module, plugin["class_name"])

