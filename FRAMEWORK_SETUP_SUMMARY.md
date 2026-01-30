# Multi-Framework IoT Comparison System

## Overview

You now have a complete, production-ready system for comparing STGen with other IoT testing frameworks (Gotham, GothX) across identical scenarios.

## What Was Created

### Core Files

1. **compare_frameworks.py** (437 lines)
   - Main orchestrator for multi-framework comparison
   - Handles STGen, Gotham, and GothX execution
   - Generates comparative reports (Markdown + JSON)
   - Automatically extracts and compares metrics

2. **framework_adapters.py** (274 lines)
   - Adapter pattern for framework integration
   - GothamAdapter: Full implementation with auto-detection
   - GothXAdapter: Placeholder for future integration
   - Helper functions for validation and diagnostics

3. **FRAMEWORK_COMPARISON.md** (380+ lines)
   - Comprehensive documentation
   - Installation instructions
   - Usage examples
   - Troubleshooting guide
   - Integration patterns

### Utility Files

4. **validate_setup.py**
   - Validates your framework setup
   - Checks for dependencies
   - Provides installation guidance
   - Run with: `python3 validate_setup.py`

5. **run_test.py**
   - Simple test runner
   - Lists available scenarios
   - Runs comparison with one command
   - Run with: `python3 run_test.py smart_home stgen`

6. **QUICKSTART.md**
   - User-friendly quick start guide
   - Common use cases
   - Troubleshooting tips
   - Results interpretation

## Current Status

### ✓ Working

- **STGen**: Fully functional
- **Framework Comparison Tool**: Ready to use
- **Scenarios**: 8 pre-configured scenarios available
- **Report Generation**: Markdown and JSON output

### ⏳ Optional/Pending

- **Gotham Integration**: Ready to integrate, needs installation
- **GothX**: Placeholder, awaiting framework specification

## Getting Started

### 1. Validate Your Setup

```bash
python3 validate_setup.py
```

This will show you:
- ✓ STGen status
- ✓ Available scenarios
- ⚠ Gotham installation status

### 2. Run Your First Comparison

```bash
python3 run_test.py smart_home stgen
```

This will:
1. Run STGen on the smart_home scenario
2. Generate detailed metrics
3. Save results to `framework_comparison.json` and `framework_comparison.md`

### 3. View Results

```bash
cat framework_comparison.md
cat framework_comparison.json
```

## Directory Structure

```
STGen_Future_Present/
├── compare_frameworks.py          # Main comparison tool
├── framework_adapters.py          # Framework integrations
├── validate_setup.py              # Setup validator
├── run_test.py                    # Simple test runner
├── QUICKSTART.md                  # Quick start guide
├── FRAMEWORK_COMPARISON.md        # Detailed documentation
├── FRAMEWORK_SETUP_SUMMARY.md     # This file
├── stgen/                         # STGen framework
├── configs/
│   └── scenarios/                 # 8 pre-configured scenarios
└── results/                       # Output directory (auto-created)
```

## Typical Workflow

### Step 1: Run Baseline Test with STGen

```bash
python3 run_test.py smart_home stgen
# Results → framework_comparison.json
```

### Step 2: (Optional) Install and Compare with Gotham

```bash
# Clone Gotham
git clone https://github.com/xsaga/gotham-iot-testbed.git

# Install (in gotham-iot-testbed directory)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make

# Compare
cd ../STGen_Future_Present
python3 compare_frameworks.py --scenario smart_home --frameworks stgen,gotham
```

### Step 3: Identify and Integrate GothX

Once you determine what GothX actually is:
1. Add it to framework_adapters.py following the GothamAdapter pattern
2. Run: `python3 compare_frameworks.py --frameworks stgen,gotham,gothx`

### Step 4: Batch Testing

Create a script to test multiple scenarios:

```bash
for scenario in smart_home smart_agriculture connected_vehicle smart_factory; do
    python3 run_test.py $scenario stgen
    mv framework_comparison.json results/${scenario}_comparison.json
done
```

## Output Formats

### Markdown Report (framework_comparison.md)

Human-readable comparison with:
- Scenario metadata
- Metric comparison table
- Winner analysis
- Detailed results per framework

Example:
```markdown
# Framework Comparison Report: smart_home

| Metric | STGen | Gotham |
|--------|-------|--------|
| Packets Sent | 1542 | 1531 |
| Avg Latency (ms) | 45.3 | 52.1 |
| Winner | ✓ | |
```

### JSON Report (framework_comparison.json)

Machine-readable format with:
- Full metric data
- Timestamp and metadata
- Per-framework execution details
- Comparison results

Example:
```json
{
  "scenario": "smart_home",
  "timestamp": "2024-01-15T10:30:45",
  "frameworks": {
    "stgen": {
      "metrics": {...},
      "execution_time": 45.3
    }
  }
}
```

## Key Metrics

The comparison system automatically extracts:

- **Protocol**: Protocol used (MQTT, CoAP, etc.)
- **Packets Sent**: Total packets transmitted
- **Packets Lost**: Dropped packets
- **Latency**: Message delivery time
- **Throughput**: Data transfer rate
- **CPU Usage**: Processor utilization
- **Memory Usage**: RAM consumption
- **Execution Time**: Test duration

## Integration with Your Research

This system is designed for:

1. **Paper Writing**: Use generated Markdown tables directly in papers
2. **Data Collection**: Batch run multiple scenarios and scenarios
3. **Comparison Studies**: Side-by-side framework analysis
4. **Benchmarking**: Reproducible framework performance testing
5. **Reproducibility**: All runs are timestamped and logged

## Troubleshooting

### Common Issues

**Q: "STGen executable not found"**
```bash
python3 -m stgen.main --help
```

**Q: Results directory not found**
```bash
mkdir -p results
```

**Q: Gotham not detected**
```bash
python3 compare_frameworks.py --gotham-path /path/to/gotham-iot-testbed
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
python3 compare_frameworks.py --scenario smart_home --frameworks stgen
```

## Advanced Features

### Custom Timeout (for Gotham/GNS3)

```bash
python3 compare_frameworks.py --scenario smart_home --timeout 600
```

### Specify Gotham Location

```bash
python3 compare_frameworks.py --gotham-path ~/my-gotham --scenario smart_home
```

### List Available Frameworks

```bash
python3 framework_adapters.py
```

## Future Enhancements

### 1. GothX Integration

Once GothX framework is identified:
- Add to framework_adapters.py
- Create GothXAdapter class
- Update compare_frameworks.py to handle it

### 2. Extended Metrics

Could add:
- Power consumption measurements
- Network bandwidth analysis
- Security testing metrics
- Scalability benchmarks

### 3. Visualization

Could add:
- Matplotlib/Plotly graphs
- Comparative charts
- Performance dashboards
- Real-time monitoring

### 4. Batch Testing

Could implement:
- Multi-scenario runners
- Automated result aggregation
- Statistical analysis
- Trend analysis

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         compare_frameworks.py                   │
│        (Main Orchestrator)                      │
└────┬─────────────────┬──────────────────┬──────┘
     │                 │                  │
     ▼                 ▼                  ▼
┌──────────┐    ┌──────────┐      ┌──────────┐
│ STGen    │    │ Gotham   │      │ GothX    │
│ Direct   │    │ Adapter  │      │ Adapter  │
│ Invocation    │ (Auto-   │      │(Placeholder)
│              │  detect) │      │          │
└────┬─────┘   └────┬──────┘      └────┬──────┘
     │              │                  │
     └──────┬───────┴──────┬───────────┘
            │              │
            ▼              ▼
       ┌──────────┬──────────────┐
       │ Results  │  Metrics     │
       │ Parser   │  Extraction  │
       └────┬─────┴──────┬───────┘
            │            │
            ▼            ▼
       ┌─────────────────────────┐
       │  Comparison Report Gen  │
       │  (JSON + Markdown)      │
       └─────────────────────────┘
```

## Files Reference

| File | Purpose | Size |
|------|---------|------|
| compare_frameworks.py | Main orchestrator | 437 lines |
| framework_adapters.py | Framework adapters | 274 lines |
| FRAMEWORK_COMPARISON.md | Detailed docs | 380+ lines |
| QUICKSTART.md | Quick start guide | 250+ lines |
| validate_setup.py | Setup validation | 200+ lines |
| run_test.py | Simple test runner | 100+ lines |

## Command Reference

```bash
# Setup validation
python3 validate_setup.py

# Run test with defaults (smart_home, stgen)
python3 run_test.py

# Run on specific scenario
python3 run_test.py smart_agriculture stgen

# Compare multiple frameworks
python3 compare_frameworks.py --scenario smart_home --frameworks stgen,gotham

# Specify Gotham location
python3 compare_frameworks.py --gotham-path /home/user/gotham --scenario smart_home

# List frameworks
python3 framework_adapters.py

# Custom timeout
python3 compare_frameworks.py --scenario smart_home --timeout 600
```

## Next Steps

1. **Try it**: `python3 validate_setup.py`
2. **Run test**: `python3 run_test.py smart_home stgen`
3. **View results**: `cat framework_comparison.md`
4. **Install Gotham** (optional): Follow GitHub instructions
5. **Identify GothX**: Determine actual framework and integrate
6. **Scale up**: Run multiple scenarios for your research

## Support & Documentation

- **Quick Start**: See QUICKSTART.md
- **Detailed Docs**: See FRAMEWORK_COMPARISON.md
- **STGen Docs**: See stgen/ and docs/ directories
- **Gotham Docs**: https://github.com/xsaga/gotham-iot-testbed

---

**Your multi-framework comparison system is ready to use!** 🚀

Start with: `python3 validate_setup.py`
