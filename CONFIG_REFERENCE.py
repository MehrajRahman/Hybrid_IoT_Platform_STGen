#!/usr/bin/env python3
"""
Framework Configuration Reference
Shows how to customize and extend the comparison system
"""

from dataclasses import dataclass
from typing import Callable, Dict, Any

# ============================================================================
# FRAMEWORK CONFIGURATION EXAMPLES
# ============================================================================

@dataclass
class FrameworkConfig:
    """Configuration for a test framework."""
    name: str                      # Framework name (stgen, gotham, gothx)
    executable: str                # Command/path to run the framework
    config_path: str               # Path to configuration file
    result_parser: Callable        # Function to parse results
    supports_scenarios: bool = True  # Whether framework supports scenarios
    timeout: int = 300             # Default timeout in seconds


# ============================================================================
# DEFAULT CONFIGURATIONS
# ============================================================================

# STGen Configuration
STGEN_CONFIG = FrameworkConfig(
    name="stgen",
    executable="python3 -m stgen.main",
    config_path="configs/",
    result_parser=None,  # Built-in parser in compare_frameworks.py
    supports_scenarios=True,
    timeout=300
)

# Gotham Configuration (when installed)
GOTHAM_CONFIG = FrameworkConfig(
    name="gotham",
    executable="python3 src/run_scenario_gotham.py",
    config_path="",
    result_parser=None,  # GothamAdapter handles parsing
    supports_scenarios=True,
    timeout=600  # GNS3 can be slow
)

# GothX Configuration (placeholder)
GOTHX_CONFIG = FrameworkConfig(
    name="gothx",
    executable="python3 -m gothx",
    config_path="",
    result_parser=None,
    supports_scenarios=True,
    timeout=300
)


# ============================================================================
# CUSTOMIZATION EXAMPLES
# ============================================================================

"""
Example 1: Increase Timeout for Slow Frameworks
============================================

    config = GOTHAM_CONFIG
    config.timeout = 900  # 15 minutes for GNS3 emulation
"""

"""
Example 2: Use Custom Configuration Path
============================================

    config = STGEN_CONFIG
    config.config_path = "my_configs/"
"""

"""
Example 3: Add Custom Framework
============================================

# 1. Create adapter in framework_adapters.py:
class MyFrameworkAdapter:
    def run_scenario(self, scenario_name):
        # Implementation here
        return {"metrics": {...}}

# 2. Configure it:
MY_FRAMEWORK_CONFIG = FrameworkConfig(
    name="my_framework",
    executable="python3 my_framework",
    config_path="config/",
    result_parser=None,
    supports_scenarios=True,
    timeout=300
)

# 3. Use in compare_frameworks.py:
python3 compare_frameworks.py --frameworks stgen,my_framework
"""


# ============================================================================
# SCENARIO CONFIGURATION
# ============================================================================

AVAILABLE_SCENARIOS = {
    "smart_home": {
        "description": "Smart home IoT with lighting, temperature, security",
        "devices": ["smart_lights", "thermostat", "door_sensor", "motion_sensor"],
        "protocol": "MQTT",
        "duration": 60,
        "clients": 4
    },
    "smart_agriculture": {
        "description": "Agricultural sensor network",
        "devices": ["soil_sensor", "weather_station", "irrigation_controller"],
        "protocol": "CoAP",
        "duration": 60,
        "clients": 3
    },
    "healthcare_wearables": {
        "description": "Wearable medical devices",
        "devices": ["heart_rate_monitor", "blood_pressure", "pulse_oximeter"],
        "protocol": "MQTT",
        "duration": 60,
        "clients": 3
    },
    "connected_vehicle": {
        "description": "Connected vehicle telemetry",
        "devices": ["gps", "obd_reader", "door_lock", "infotainment"],
        "protocol": "MQTT",
        "duration": 60,
        "clients": 4
    },
    "smart_factory": {
        "description": "Industrial IoT / Industry 4.0",
        "devices": ["machine_controller", "temperature_sensor", "pressure_sensor"],
        "protocol": "MQTT",
        "duration": 60,
        "clients": 5
    },
    "environmental_monitoring": {
        "description": "Environmental sensors network",
        "devices": ["air_quality", "temperature", "humidity", "noise_level"],
        "protocol": "CoAP",
        "duration": 60,
        "clients": 4
    },
    "event_driven_bursts": {
        "description": "Event-driven traffic with bursts",
        "devices": ["alarm", "motion_detector", "smoke_detector"],
        "protocol": "MQTT",
        "duration": 60,
        "clients": 3
    },
    "stress_testing": {
        "description": "Load/stress test with high message volume",
        "devices": ["high_frequency_sensor"] * 10,
        "protocol": "MQTT",
        "duration": 120,
        "clients": 10
    }
}


# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

METRIC_DEFINITIONS = {
    "sent": "Total packets/messages sent",
    "received": "Total packets/messages received",
    "loss": "Packet loss rate (%)",
    "latency": "Average message latency (ms)",
    "throughput": "Data throughput (Mbps)",
    "cpu_usage": "CPU utilization (%)",
    "memory_usage": "Memory usage (MB)",
    "battery_drain": "Battery drain rate (%/min)",
    "protocol": "Protocol used (MQTT, CoAP, etc)",
    "execution_time": "Test execution time (seconds)"
}


# ============================================================================
# CUSTOM COMPARISON WEIGHTS (for scoring)
# ============================================================================

METRIC_WEIGHTS = {
    "latency": 0.25,        # Latency is important (25%)
    "throughput": 0.20,     # Throughput matters (20%)
    "packet_loss": 0.20,    # Reliability (20%)
    "cpu_usage": 0.15,      # Efficiency (15%)
    "memory_usage": 0.10,   # Resource usage (10%)
    "battery_drain": 0.10   # Power efficiency (10%)
}


# ============================================================================
# ADVANCED CUSTOMIZATION
# ============================================================================

"""
How to Create a Custom Adapter
===============================

1. Create new file: framework_adapters.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class FrameworkAdapter(ABC):
    @abstractmethod
    def run_scenario(self, scenario_name: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate_installation(self) -> bool:
        pass

class MyFrameworkAdapter(FrameworkAdapter):
    def __init__(self, timeout=300):
        self.timeout = timeout
    
    def run_scenario(self, scenario_name: str) -> Dict[str, Any]:
        # Your implementation here
        return {
            "status": "completed",
            "metrics": {
                "latency": 50.5,
                "throughput": 2.5,
                "loss": 0.5
            }
        }
    
    def validate_installation(self) -> bool:
        # Check if framework is installed
        return True


2. Update compare_frameworks.py to use it:

    elif fw.name == "my_framework":
        return self._run_my_framework(fw)

    def _run_my_framework(self, fw: FrameworkConfig) -> Dict[str, Any]:
        from framework_adapters import MyFrameworkAdapter
        adapter = MyFrameworkAdapter(timeout=fw.timeout)
        return adapter.run_scenario(self.scenario_name)


3. Use it:

    python3 compare_frameworks.py --frameworks stgen,my_framework
"""


# ============================================================================
# EXTENDING METRICS COLLECTION
# ============================================================================

"""
How to Add Custom Metrics
==========================

1. In framework_adapters.py, add metric collection:

    def _collect_metrics(self, results):
        return {
            "latency": self._extract_latency(results),
            "throughput": self._extract_throughput(results),
            "custom_metric": self._extract_custom_metric(results)
        }

2. In compare_frameworks.py, update metric extraction:

    def _extract_common_metrics(self, fw_results):
        metrics = {}
        for metric in ["latency", "throughput", "custom_metric"]:
            if metric in fw_results.get("metrics", {}):
                metrics[metric] = fw_results["metrics"][metric]
        return metrics
"""


# ============================================================================
# BATCH TESTING SCRIPT EXAMPLE
# ============================================================================

"""
Save as: batch_test.py

#!/usr/bin/env python3

import subprocess
from pathlib import Path
import json

scenarios = [
    "smart_home",
    "smart_agriculture",
    "connected_vehicle",
    "smart_factory"
]

frameworks = "stgen,gotham"

results = {}

for scenario in scenarios:
    print(f"Testing {scenario}...")
    
    cmd = [
        "python3", "compare_frameworks.py",
        "--scenario", scenario,
        "--frameworks", frameworks,
        "--timeout", "600"
    ]
    
    subprocess.run(cmd)
    
    # Save results
    if Path("framework_comparison.json").exists():
        with open("framework_comparison.json") as f:
            results[scenario] = json.load(f)
        
        # Rename for archival
        Path("framework_comparison.json").rename(
            f"results/{scenario}_comparison.json"
        )

# Write summary
with open("batch_results_summary.json", "w") as f:
    json.dump(results, f, indent=2)

print("Batch testing complete!")
"""


# ============================================================================
# PROTOCOL CONFIGURATION
# ============================================================================

PROTOCOL_CONFIGS = {
    "mqtt": {
        "name": "MQTT",
        "port": 1883,
        "broker": "mosquitto",
        "qos_levels": [0, 1, 2]
    },
    "coap": {
        "name": "CoAP",
        "port": 5683,
        "protocol": "UDP",
        "block_size": 1024
    },
    "srtp": {
        "name": "SRTP",
        "port": 5000,
        "protocol": "RTP/UDP",
        "encryption": "AES"
    },
    "custom_udp": {
        "name": "Custom UDP",
        "port": 9999,
        "protocol": "UDP",
        "packet_size": 512
    }
}


# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

OUTPUT_FORMATS = {
    "markdown": {
        "extension": ".md",
        "description": "Human-readable Markdown tables",
        "use_case": "Papers, reports, documentation"
    },
    "json": {
        "extension": ".json",
        "description": "Machine-readable JSON",
        "use_case": "Data processing, automation, databases"
    },
    "csv": {
        "extension": ".csv",
        "description": "Excel/spreadsheet compatible",
        "use_case": "Data analysis, visualization"
    }
}


# ============================================================================
# EXAMPLE USAGE IN CODE
# ============================================================================

if __name__ == "__main__":
    print("Framework Configuration Reference")
    print("=" * 50)
    
    print("\nAvailable Scenarios:")
    for scenario, config in AVAILABLE_SCENARIOS.items():
        print(f"\n  {scenario}:")
        print(f"    {config['description']}")
        print(f"    Devices: {len(config['devices'])}")
        print(f"    Protocol: {config['protocol']}")
    
    print("\n\nMetric Definitions:")
    for metric, definition in METRIC_DEFINITIONS.items():
        print(f"  {metric}: {definition}")
    
    print("\n\nDefault Configurations:")
    print(f"  STGen: {STGEN_CONFIG.timeout}s timeout")
    print(f"  Gotham: {GOTHAM_CONFIG.timeout}s timeout")
    print(f"  GothX: {GOTHX_CONFIG.timeout}s timeout")
