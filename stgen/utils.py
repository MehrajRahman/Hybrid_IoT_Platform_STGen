# stgen/utils.py
"""
@file utils.py
@brief Utility functions for STGen framework.
@details Contains helper functions for configuration loading/validation, 
         file system operations, data formatting, and statistical calculations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# @brief Logger for the utility module
_LOG = logging.getLogger("stgen.utils")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    @brief Load configuration from JSON file.

    @details Reads a JSON file from the specified path and parses it into a dictionary.

    @param config_path Path to the configuration file.
    @return Dict[str, Any] The parsed configuration dictionary.

    @exception FileNotFoundError If the file does not exist.
    @exception ValueError If the file contains invalid JSON.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        cfg = json.loads(path.read_text())
        _LOG.debug(f"Loaded config from {config_path}")
        return cfg
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}")


def load_scenario(scenario_name: str) -> Dict[str, Any]:
    """
    @brief Load predefined scenario configuration.

    @details Looks for a JSON file in `configs/scenarios/` matching the given name.

    @param scenario_name Name of scenario (e.g., "smart_home", without extension).
    @return Dict[str, Any] The scenario configuration dictionary.
    """
    scenario_path = Path("configs/scenarios") / f"{scenario_name}.json"
    return load_config(str(scenario_path))


def list_available_scenarios() -> List[str]:
    """
    @brief Get list of available scenario names.

    @details Scans the `configs/scenarios` directory for .json files.
    @return List[str] A list of scenario filenames without extensions.
    """
    scenarios_dir = Path("configs/scenarios")
    if not scenarios_dir.exists():
        return []

    return [f.stem for f in scenarios_dir.glob("*.json")]


def list_available_protocols() -> List[str]:
    """
    @brief Get list of available protocol implementations.

    @details Scans the `protocols` directory for subdirectories containing an `__init__.py`.
             Ignores directories starting with `_`.

    @return List[str] A list of valid protocol names.
    """
    protocols_dir = Path("protocols")
    if not protocols_dir.exists():
        return []

    protocols = []
    for item in protocols_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            # Check if it has __init__.py
            if (item / "__init__.py").exists():
                protocols.append(item.name)

    return protocols


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    @brief Merge two configuration dictionaries.

    @details Creates a shallow copy of the base dictionary and updates it with 
             values from the override dictionary.

    @param base The base configuration dictionary.
    @param override The dictionary containing values to override or add.
    @return Dict[str, Any] The merged configuration.
    """
    merged = base.copy()
    merged.update(override)
    return merged


def validate_config(cfg: Dict[str, Any]) -> bool:
    """
    @brief Validate configuration has required fields and correct types.

    @details Checks for existence of: protocol, server_ip, server_port, num_clients, duration.
             Validates that `num_clients` is non-negative and `duration` is positive.

    @param cfg Configuration dictionary to validate.
    @return bool True if valid.

    @exception ValueError If required fields are missing or types are incorrect.
    """
    required_fields = ["protocol", "server_ip",
                       "server_port", "num_clients", "duration"]

    missing = [field for field in required_fields if field not in cfg]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Validate types
    # Allow `num_clients == 0` for server-only / core nodes (no local clients).
    if not isinstance(cfg["num_clients"], int) or cfg["num_clients"] < 0:
        raise ValueError("num_clients must be a non-negative integer")

    if not isinstance(cfg["duration"], (int, float)) or cfg["duration"] <= 0:
        raise ValueError("duration must be a positive number")

    return True


def format_latency(latency_ms: float) -> str:
    """
    @brief Format latency value for human-readable display.

    @details Auto-scales between microseconds, milliseconds, and seconds.

    @param latency_ms Latency in milliseconds.
    @return str Formatted string (e.g., "500µs", "10.5ms").
    """
    if latency_ms < 1:
        return f"{latency_ms*1000:.0f}µs"
    elif latency_ms < 1000:
        return f"{latency_ms:.2f}ms"
    else:
        return f"{latency_ms/1000:.2f}s"


def format_throughput(messages: int, duration_sec: float) -> str:
    """
    @brief Format throughput for display.

    @details Switches between msg/s and msg/min based on rate.

    @param messages Total messages count.
    @param duration_sec Duration in seconds.
    @return str Formatted string (e.g., "50.0 msg/s").
    """
    rate = messages / duration_sec if duration_sec > 0 else 0
    if rate < 1:
        return f"{rate*60:.1f} msg/min"
    else:
        return f"{rate:.1f} msg/s"


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    @brief Calculate percentile from list of values.

    @details sorts the list and finds the value at the specific index.

    @param values List of numeric values.
    @param percentile Percentile to calculate (0-100).
    @return float The value at the specified percentile, or 0.0 if list is empty.
    """
    if not values:
        return 0.0

    sorted_vals = sorted(values)
    index = int(len(sorted_vals) * (percentile / 100.0))
    index = min(index, len(sorted_vals) - 1)
    return sorted_vals[index]


def save_json(data: Dict[str, Any], filepath: str) -> None:
    """
    @brief Save dictionary as JSON file.

    @details Creates parent directories if they don't exist.

    @param data Data dictionary to save.
    @param filepath Output file path.
    @return None
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    _LOG.debug(f"Saved JSON to {filepath}")


def load_json(filepath: str) -> Dict[str, Any]:
    """
    @brief Load JSON file.

    @param filepath Path to JSON file.
    @return Dict[str, Any] Loaded data.
    """
    with open(filepath, 'r') as f:
        return json.load(f)
