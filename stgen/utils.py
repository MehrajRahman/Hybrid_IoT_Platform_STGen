"""
Utility functions for STGen framework.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

_LOG = logging.getLogger("stgen.utils")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Dict with configuration
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
    Load predefined scenario configuration.
    
    Args:
        scenario_name: Name of scenario (e.g., "smart_home")
        
    Returns:
        Dict with scenario configuration
    """
    scenario_path = Path("configs/scenarios") / f"{scenario_name}.json"
    return load_config(str(scenario_path))


def list_available_scenarios() -> List[str]:
    """Get list of available scenario names."""
    scenarios_dir = Path("configs/scenarios")
    if not scenarios_dir.exists():
        return []
    
    return [f.stem for f in scenarios_dir.glob("*.json")]


def list_available_protocols() -> List[str]:
    """Get list of available protocol implementations."""
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
    Merge two configuration dictionaries.
    
    Args:
        base: Base configuration
        override: Values to override
        
    Returns:
        Merged configuration
    """
    merged = base.copy()
    merged.update(override)
    return merged


def validate_config(cfg: Dict[str, Any]) -> bool:
    """
    Validate configuration has required fields.
    
    Args:
        cfg: Configuration to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["protocol", "server_ip", "server_port", "num_clients", "duration"]
    
    missing = [field for field in required_fields if field not in cfg]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    # Validate types
    if not isinstance(cfg["num_clients"], int) or cfg["num_clients"] <= 0:
        raise ValueError("num_clients must be a positive integer")
    
    if not isinstance(cfg["duration"], (int, float)) or cfg["duration"] <= 0:
        raise ValueError("duration must be a positive number")
    
    return True


def format_latency(latency_ms: float) -> str:
    """Format latency value for display."""
    if latency_ms < 1:
        return f"{latency_ms*1000:.0f}µs"
    elif latency_ms < 1000:
        return f"{latency_ms:.2f}ms"
    else:
        return f"{latency_ms/1000:.2f}s"


def format_throughput(messages: int, duration_sec: float) -> str:
    """Format throughput for display."""
    rate = messages / duration_sec if duration_sec > 0 else 0
    if rate < 1:
        return f"{rate*60:.1f} msg/min"
    else:
        return f"{rate:.1f} msg/s"


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate percentile from list of values.
    
    Args:
        values: List of numeric values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not values:
        return 0.0
    
    sorted_vals = sorted(values)
    index = int(len(sorted_vals) * (percentile / 100.0))
    index = min(index, len(sorted_vals) - 1)
    return sorted_vals[index]


def save_json(data: Dict[str, Any], filepath: str) -> None:
    """
    Save dictionary as JSON file.
    
    Args:
        data: Data to save
        filepath: Output file path
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    _LOG.debug(f"Saved JSON to {filepath}")


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded data
    """
    with open(filepath, 'r') as f:
        return json.load(f)