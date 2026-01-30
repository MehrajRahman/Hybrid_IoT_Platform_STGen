# IoT Framework Comparison Tool

Comprehensive comparison framework for IoT protocol testing tools: **STGen**, **Gotham**, and **GothX**.

## Overview

This tool allows you to run identical scenarios across multiple IoT testing frameworks and generate comparative reports with metrics analysis.

## Supported Frameworks

### 1. **STGen** (Fully Integrated)
- **Status**: ✓ Integrated
- **Type**: Python-based IoT protocol testing framework
- **Location**: This repository
- **Capabilities**: MQTT, CoAP, SRTP, custom UDP protocols
- **Usage**: `python -m stgen.main --scenario smart_home`

### 2. **Gotham IoT Testbed** (Supported)
- **Status**: ✓ Adapter available
- **Type**: GNS3-based IoT emulation platform
- **Repository**: https://github.com/xsaga/gotham-iot-testbed
- **Requires**: GNS3 server, Docker, Python venv
- **Usage**: Via `framework_adapters.GothamAdapter`

### 3. **GothX** (Placeholder)
- **Status**: ⏳ Awaiting specification
- **Type**: To be determined
- **Status**: Not yet implemented
- **Next Steps**: Specify actual framework and update adapter

## Installation

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get install python3-pip python3-venv docker.io

# macOS
brew install python docker
```

### STGen Setup (Already Installed)

```bash
source myenv/bin/activate
pip install -r requirements.txt
```

### Gotham Setup (Optional)

```bash
# Clone Gotham repository
git clone https://github.com/xsaga/gotham-iot-testbed.git
cd gotham-iot-testbed

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build Docker images (takes ~30 minutes)
make

# Install GNS3 (https://www.gns3.com/)
# Then set up templates and topology
python3 src/create_templates.py
python3 src/create_topology_gotham.py
```

## Usage

### Quick Start: Compare STGen and Gotham

```bash
# Basic comparison on smart_home scenario
python compare_frameworks.py --scenario smart_home

# Compare on smart_agriculture scenario
python compare_frameworks.py --scenario smart_agriculture --frameworks stgen,gotham

# With custom timeout (Gotham may need more time)
python compare_frameworks.py --scenario smart_home --timeout 600
```

### List Available Frameworks

```bash
python compare_frameworks.py --list-frameworks
python framework_adapters.py  # Also shows installation instructions
```

### Advanced Usage

```bash
# Specify Gotham repository path explicitly
python compare_frameworks.py \
  --scenario smart_home \
  --gotham-path /home/user/gotham-iot-testbed \
  --frameworks stgen,gotham

# Custom output file
python compare_frameworks.py \
  --scenario smart_agriculture \
  --output comparison_results.md

# Generate both Markdown and JSON reports
# (Automatic - generates .md and .json versions)
```

## Available Scenarios

Run any scenario name from the following:

- `smart_home` - Residential IoT devices
- `smart_agriculture` - Farm sensors and irrigation
- `healthcare_wearables` - Medical device data
- `connected_vehicle` - Automotive IoT
- `smart_factory` - Industrial IoT
- `environmental_monitoring` - Weather and pollution sensors
- `event_driven_bursts` - Bursty traffic patterns
- `stress_testing` - High-load scenarios

## Output

The comparison tool generates:

### 1. **Markdown Report** (`framework_comparison.md`)
- Executive summary with status and execution times
- Metrics comparison table
- Per-framework detailed results
- Winner analysis for each metric category

### 2. **JSON Summary** (`framework_comparison.json`)
- Machine-readable results
- Timestamp and scenario information
- Framework list
- Complete result data

### Example Report Structure

```
# IoT Framework Comparison Report

**Scenario:** smart_home
**Date:** 2024-01-11T14:30:45.123456
**Frameworks:** stgen, gotham

## Executive Summary

| Framework | Status | Execution Time (s) |
|-----------|--------|-------------------|
| stgen | ✓ Pass | 15.23 |
| gotham | ✓ Pass | 45.67 |

## Metrics Comparison

| Metric | stgen | gotham | Δ vs stgen |
|--------|-------|--------|-----------|
| sent | 15000 | 14892 | -0.7% |
| lat_avg_ms | 12.45 | 18.92 | +52% |
| loss | 0.001 | 0.005 | +400% |

## Winner Analysis

### Latency
**stgen:** 12.45ms

### Throughput
**stgen:** 15000 packets
```

## Framework Adapters

Each framework has an adapter for standardized testing:

### GothamAdapter (`framework_adapters.py`)

```python
from framework_adapters import GothamAdapter

adapter = GothamAdapter(repo_path="/path/to/gotham-iot-testbed")
results = adapter.run_scenario("smart_home")
```

Methods:
- `run_scenario(scenario_name)` - Run a test scenario
- `validate_installation()` - Check if framework is properly installed
- `get_info()` - Get framework information

## Metrics Collected

Both frameworks report on:

- **Latency** (ms): min, average, p95, p99
- **Throughput**: packets sent/received, bits per second
- **Reliability**: packet loss rate, delivery ratio
- **Timing**: scenario execution time
- **Framework-specific**:
  - STGen: Energy consumption, protocol overhead
  - Gotham: Network topology info, pcap files

## Troubleshooting

### STGen Not Found
```bash
# Verify STGen is installed
python -m stgen.main --help

# Install if needed
pip install -r requirements.txt
```

### Gotham Not Found
```bash
# Clone and set up Gotham
git clone https://github.com/xsaga/gotham-iot-testbed.git
cd gotham-iot-testbed
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make
```

### Gotham Errors

```bash
# Check if GNS3 server is running
# Start GNS3 on your machine or ensure GNS3 server service is active

# Verify Docker images are built
cd gotham-iot-testbed
make  # Rebuild if needed

# Check Gotham repository path
python framework_adapters.py  # Shows detected path
```

### Timeout Issues

```bash
# Increase timeout for slow systems
python compare_frameworks.py --timeout 900  # 15 minutes
```

## Integration: Adding a New Framework

To add support for a new framework (e.g., a real GothX):

1. **Create an adapter** in `framework_adapters.py`:

```python
class GothXAdapter:
    def __init__(self, executable_path: str = "gothx", timeout: int = 300):
        self.executable = executable_path
        self.timeout = timeout
    
    def run_scenario(self, scenario_name: str) -> Dict[str, Any]:
        # Implement actual framework execution
        pass
    
    def validate_installation(self) -> bool:
        # Check if framework is installed
        pass
```

2. **Update `compare_frameworks.py`**:

```python
def _run_gothx(self, fw: FrameworkConfig) -> Dict[str, Any]:
    """Run GothX framework using GothXAdapter."""
    from framework_adapters import GothXAdapter
    
    start_time = time.time()
    adapter = GothXAdapter(timeout=fw.timeout)
    result = adapter.run_scenario(self.scenario_name)
    result["execution_time"] = time.time() - start_time
    return result
```

3. **Add to default frameworks**:

```bash
python compare_frameworks.py --frameworks stgen,gotham,gothx
```

## Files Overview

- `compare_frameworks.py` - Main comparison orchestrator
- `framework_adapters.py` - Framework adapters for Gotham and others
- `run_comparison_test.py` - Legacy comparison script (protocol-specific)
- `stgen/comparator.py` - STGen's built-in protocol comparator

## Example Workflow

```bash
# 1. List available frameworks
python framework_adapters.py

# 2. Run comparison
python compare_frameworks.py \
  --scenario smart_home \
  --frameworks stgen,gotham \
  --output smart_home_comparison.md

# 3. View results
cat smart_home_comparison.md
cat smart_home_comparison.json | jq .

# 4. Analyze metrics
grep -A 20 "Metrics Comparison" smart_home_comparison.md
```

## References

- **STGen**: This repository
- **Gotham**: https://github.com/xsaga/gotham-iot-testbed
- **GNS3**: https://www.gns3.com/

## Citation

If you use this comparison framework in research, please cite:

```bibtex
@software{stgen_comparator2024,
  title={IoT Framework Comparison Tool for STGen, Gotham, and GothX},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/stgen}
}
```

## Support

For issues or questions:
1. Check framework-specific documentation
2. Run `python framework_adapters.py` for diagnostic information
3. Review framework logs and output
4. Check scenario configuration files in `configs/scenarios/`

---

**Last Updated**: January 11, 2026
**Status**: STGen ✓ | Gotham ✓ | GothX ⏳
