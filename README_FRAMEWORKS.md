# STGen Framework Comparison System

## Overview

A complete, production-ready system for comparing multiple IoT testing frameworks (STGen, Gotham, GothX) on identical scenarios with automatic metric extraction and comparative reporting.

## Quick Start (30 seconds)

```bash
# 1. Validate setup
python3 validate_setup.py

# 2. Run first comparison
python3 run_test.py smart_home stgen

# 3. View results
cat framework_comparison.md
```

## What You Get

### ✓ Complete Framework Comparison
- Run multiple frameworks on same scenario
- Automatic metric extraction
- Side-by-side performance comparison
- Machine-readable (JSON) and human-readable (Markdown) outputs

### ✓ Flexible Integration
- Works with STGen (built-in)
- Supports Gotham (with GothamAdapter)
- Ready for GothX (once identified)
- Extensible adapter pattern for new frameworks

### ✓ 8 Pre-Configured Scenarios
- smart_home - Smart home IoT
- smart_agriculture - Agricultural sensors
- healthcare_wearables - Wearable medical devices
- connected_vehicle - Vehicle telemetry
- smart_factory - Industrial IoT
- environmental_monitoring - Environmental sensors
- event_driven_bursts - Event-driven traffic
- stress_testing - Load testing

### ✓ Comprehensive Documentation
- QUICKSTART.md - Get started in 5 minutes
- FRAMEWORK_COMPARISON.md - Detailed technical guide
- FRAMEWORK_SETUP_SUMMARY.md - Architecture overview
- CONFIG_REFERENCE.py - Configuration examples

## Files Included

### Core System
| File | Purpose | Lines |
|------|---------|-------|
| `compare_frameworks.py` | Main orchestrator | 437 |
| `framework_adapters.py` | Framework adapters | 274 |
| `validate_setup.py` | Setup validator | 200+ |
| `run_test.py` | Simple test runner | 100+ |
| `CONFIG_REFERENCE.py` | Configuration examples | 350+ |

### Documentation
| File | Purpose |
|------|---------|
| `QUICKSTART.md` | Quick start guide |
| `FRAMEWORK_COMPARISON.md` | Technical documentation |
| `FRAMEWORK_SETUP_SUMMARY.md` | System overview |
| This file | README and index |

## Installation

### Requirements
- Python 3.7+
- STGen (included)
- MQTT broker (for STGen testing)
- (Optional) Gotham from https://github.com/xsaga/gotham-iot-testbed

### Setup
```bash
# No additional installation needed!
# STGen is already in your workspace

# Optional: Install Gotham
git clone https://github.com/xsaga/gotham-iot-testbed.git
cd gotham-iot-testbed
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && make
```

## Usage

### Run Setup Validation
```bash
python3 validate_setup.py
```
Shows: ✓ STGen status, ✓ Scenarios available, ✗ Gotham status

### Run Single Framework Test
```bash
python3 run_test.py smart_home stgen
```
Generates: `framework_comparison.md` + `framework_comparison.json`

### Run Multi-Framework Comparison
```bash
python3 compare_frameworks.py --scenario smart_home --frameworks stgen,gotham
```

### Run on Specific Scenario
```bash
python3 run_test.py connected_vehicle stgen
python3 run_test.py smart_agriculture stgen
python3 run_test.py smart_factory stgen
```

### Advanced Usage
```bash
# Custom Gotham location
python3 compare_frameworks.py --gotham-path /path/to/gotham --scenario smart_home

# Longer timeout (for slow frameworks)
python3 compare_frameworks.py --timeout 600 --scenario smart_home --frameworks stgen,gotham

# List frameworks
python3 framework_adapters.py
```

## Example Output

### Markdown Report
```markdown
# Framework Comparison Report: smart_home

**Scenario**: smart_home - Smart home IoT with 4 devices  
**Timestamp**: 2024-01-15T10:30:45  
**Frameworks**: STGen, Gotham  

## Results

| Metric | STGen | Gotham | Winner |
|--------|-------|--------|--------|
| Packets Sent | 1542 | 1531 | - |
| Packets Lost | 12 | 8 | Gotham ✓ |
| Avg Latency (ms) | 45.3 | 52.1 | STGen ✓ |
| Throughput (Mbps) | 2.34 | 2.18 | STGen ✓ |
| CPU Usage (%) | 15.2 | 22.5 | STGen ✓ |
| Execution Time (s) | 45 | 125 | STGen ✓ |

**Overall Winner**: STGen (4/5 metrics)
```

### JSON Report
```json
{
  "scenario": "smart_home",
  "timestamp": "2024-01-15T10:30:45",
  "frameworks": {
    "stgen": {
      "status": "completed",
      "metrics": {
        "sent": 1542,
        "loss": 0.78,
        "latency": 45.3,
        "throughput": 2.34,
        "cpu_usage": 15.2
      },
      "execution_time": 45
    },
    "gotham": {
      "status": "completed",
      "metrics": {
        "sent": 1531,
        "loss": 0.52,
        "latency": 52.1,
        "throughput": 2.18,
        "cpu_usage": 22.5
      },
      "execution_time": 125
    }
  },
  "comparison": {
    "winner": "stgen",
    "score": 4,
    "reasoning": "Lower latency, higher throughput, better resource usage"
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────┐
│      compare_frameworks.py                  │
│      (Main Orchestrator)                    │
└────┬──────────────┬────────────┬─────────┘
     │              │            │
     ▼              ▼            ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│ STGen   │  │ Gotham   │  │ GothX    │
│ Direct  │  │ Adapter  │  │ Adapter  │
└────┬────┘  └────┬─────┘  └────┬─────┘
     │            │             │
     └──────┬─────┴─────┬───────┘
            │           │
            ▼           ▼
        ┌────────────────────┐
        │ Results Analysis   │
        │ Metrics Extraction │
        │ Winner Calculation │
        └────────┬───────────┘
                 │
         ┌───────┴──────────┐
         ▼                  ▼
    ┌─────────────┐  ┌──────────────┐
    │ Markdown    │  │ JSON Report  │
    │ Report      │  │              │
    └─────────────┘  └──────────────┘
```

## Workflow Examples

### Example 1: Compare STGen on All Scenarios
```bash
for scenario in smart_home smart_agriculture connected_vehicle smart_factory; do
    echo "Testing: $scenario"
    python3 run_test.py $scenario stgen
    mv framework_comparison.json results/${scenario}_results.json
done
```

### Example 2: STGen vs Gotham Comparison
```bash
python3 compare_frameworks.py --scenario smart_home --frameworks stgen,gotham
cat framework_comparison.md
```

### Example 3: Batch Test with High Timeout (for GNS3)
```bash
python3 compare_frameworks.py \
    --scenario smart_home \
    --frameworks stgen,gotham \
    --timeout 600
```

## Metrics Collected

The system automatically extracts:

| Metric | Description | Unit |
|--------|-------------|------|
| Packets Sent | Total packets transmitted | count |
| Packets Lost | Failed packets | count |
| Packet Loss % | Loss rate | % |
| Latency | Message delivery time | ms |
| Throughput | Data transfer rate | Mbps |
| CPU Usage | Processor utilization | % |
| Memory Usage | RAM consumption | MB |
| Battery Drain | Power usage rate | %/min |
| Protocol | Protocol used | - |
| Execution Time | Total test duration | seconds |

## Customization

### Add New Framework
1. Create adapter in `framework_adapters.py`:
   ```python
   class MyFrameworkAdapter:
       def run_scenario(self, scenario_name):
           return {"metrics": {...}}
   ```

2. Update `compare_frameworks.py` to call it

3. Run comparison:
   ```bash
   python3 compare_frameworks.py --frameworks stgen,my_framework
   ```

### Modify Metrics
- Edit `framework_adapters.py` to collect different metrics
- Update `_extract_common_metrics()` in `compare_frameworks.py`
- Update `METRIC_DEFINITIONS` in `CONFIG_REFERENCE.py`

### Create Custom Scenarios
Add JSON files to `configs/scenarios/` with scenario definitions.

## Troubleshooting

### STGen Not Found
```bash
python3 -m stgen.main --help
# If this works, the issue is your PATH
```

### Gotham Not Detected
```bash
python3 compare_frameworks.py --gotham-path /path/to/gotham-iot-testbed
```

### Results Directory Not Found
```bash
mkdir -p results
# Run comparison again
```

### Tests Timing Out
```bash
# Increase timeout for slow frameworks
python3 compare_frameworks.py --timeout 600
```

## Integration with Research

### For Papers
- Use generated Markdown tables directly in IEEE/ACM papers
- Cite as: "STGen Framework Comparison System v1.0"
- Include timestamp and scenario details in methodology

### For Presentations
- Export results to CSV or JSON
- Create charts using included metrics
- Show before/after comparisons

### For Reproducibility
- All results include timestamp
- Configuration is saved in JSON
- Full command line shown in reports
- Easy to re-run with same parameters

## Performance Tips

1. **Reduce Test Duration**: Edit scenario configs in `configs/scenarios/`
2. **Parallel Testing**: Run multiple scenarios in different terminals
3. **Resource Monitoring**: Monitor system resources during tests
4. **GNS3 Optimization**: Allocate sufficient resources to GNS3 VM

## Limitations

- **GothX**: Currently a placeholder, awaiting framework identification
- **Gotham**: Requires GNS3 server running (slow, ~2 minutes per scenario)
- **Metrics**: Limited to what each framework can report
- **Scenarios**: Pre-configured, can be extended

## Future Enhancements

- [ ] GothX framework integration (once identified)
- [ ] Real-time monitoring dashboard
- [ ] Statistical analysis and trend detection
- [ ] Graphical report generation (charts, graphs)
- [ ] Database backend for result archival
- [ ] CI/CD integration for automated benchmarking
- [ ] Extended metrics (power, security, reliability)

## Support & Resources

### Documentation
- **Getting Started**: See [QUICKSTART.md](QUICKSTART.md)
- **Technical Details**: See [FRAMEWORK_COMPARISON.md](FRAMEWORK_COMPARISON.md)
- **Architecture**: See [FRAMEWORK_SETUP_SUMMARY.md](FRAMEWORK_SETUP_SUMMARY.md)
- **Configuration**: See [CONFIG_REFERENCE.py](CONFIG_REFERENCE.py)

### External Resources
- **STGen**: Built into this workspace
- **Gotham**: https://github.com/xsaga/gotham-iot-testbed
- **GothX**: To be identified

### Commands Reference
```bash
validate_setup.py           # Check installation
run_test.py                 # Quick test (smart_home, stgen)
run_test.py [scenario]      # Test specific scenario
run_test.py --help          # Show help
compare_frameworks.py       # Full comparison tool
framework_adapters.py       # Framework status
```

## Quick Links

- 📖 [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- 📚 [FRAMEWORK_COMPARISON.md](FRAMEWORK_COMPARISON.md) - Detailed documentation
- 🏗️ [FRAMEWORK_SETUP_SUMMARY.md](FRAMEWORK_SETUP_SUMMARY.md) - Architecture overview
- ⚙️ [CONFIG_REFERENCE.py](CONFIG_REFERENCE.py) - Configuration examples
- 🔧 [compare_frameworks.py](compare_frameworks.py) - Main tool
- 🧩 [framework_adapters.py](framework_adapters.py) - Adapters

## License

Same as STGen project (check LICENSE file)

## Version

STGen Framework Comparison System v1.0  
Created: 2024  
Last Updated: 2024  

---

**Ready to get started?** Run `python3 validate_setup.py` now!
