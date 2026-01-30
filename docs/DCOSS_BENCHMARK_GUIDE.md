# DCOSS Paper: IoT Protocol Benchmarking Guide

## MQTT vs CoAP vs PRTP Comparison

This document provides instructions for running experiments to compare three IoT protocols for the DCOSS paper submission.

## Overview

We compare three representative IoT protocols:

| Protocol | Transport | Pattern | Reliability | Congestion Control |
|----------|-----------|---------|-------------|-------------------|
| **MQTT** | TCP | Pub/Sub | QoS 0/1/2 | TCP CC |
| **CoAP** | UDP | REST-like | CON/NON | None (optional) |
| **PRTP** | UDP | Pub/Sub | ACK/NACK | Q-Learning Based |

## Quick Start

### 1. Environment Setup

```bash
cd STGen_Future_Present

# Activate virtual environment
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify protocols are available
python -c "from stgen.utils import list_available_protocols; print(list_available_protocols())"
# Should output: ['SRTP', 'prtp', 'mqtt', 'coap']
```

### 2. Run Quick Comparison

```bash
# Quick 3-protocol comparison (50 nodes, 30 seconds)
python compare_mqtt_coap_prtp.py --nodes 50 --duration 30

# With LaTeX table output
python compare_mqtt_coap_prtp.py --nodes 100 --duration 60 --latex
```

### 3. Run Full DCOSS Benchmark

```bash
# Quick test (5 minutes)
python run_dcoss_benchmark.py --quick

# Full benchmark suite (may take 30-60 minutes)
python run_dcoss_benchmark.py --full

# Individual experiments
python run_dcoss_benchmark.py --latency --nodes 100
python run_dcoss_benchmark.py --scalability
python run_dcoss_benchmark.py --network
```

## Experiment Details

### Experiment 1: Latency Comparison

Measures end-to-end message latency under identical conditions.

```bash
python run_dcoss_benchmark.py --latency --nodes 100 --duration 60
```

**Metrics collected:**
- Average latency (ms)
- Median latency (P50)
- 95th percentile (P95)
- 99th percentile (P99)

### Experiment 2: Throughput Comparison

Measures maximum sustainable message rate.

```bash
python run_dcoss_benchmark.py --throughput --nodes 100 --duration 60
```

**Metrics collected:**
- Messages sent
- Messages received
- Delivery rate (%)
- Throughput (msg/s)

### Experiment 3: Scalability Test

Tests protocol performance as node count increases.

```bash
python run_dcoss_benchmark.py --scalability --duration 30
```

**Node counts tested:** 10, 50, 100, 500, 1000

### Experiment 4: Network Conditions Impact

Tests protocol robustness under various network impairments.

```bash
python run_dcoss_benchmark.py --network --nodes 50 --duration 30
```

**Network conditions:**
- **Ideal**: No impairment
- **WiFi**: 1% loss, 20ms delay
- **3G Cellular**: 2% loss, 100ms delay
- **Congested**: 5% loss, 50ms delay
- **Lossy**: 10% loss, 30ms delay

### Experiment 5: Reliability Test

Compares different reliability modes.

```bash
python run_dcoss_benchmark.py --reliability --nodes 50 --duration 30
```

**Configurations tested:**
- MQTT QoS 0, 1, 2
- CoAP NON, CON
- PRTP Unreliable, Reliable

## Output Files

Results are saved to `results/dcoss_benchmark_<timestamp>/`:

```
dcoss_benchmark_20260126_123456/
├── benchmark_report.json     # Complete results
├── summary.txt               # Human-readable summary
└── latex_tables.tex          # Tables for paper
```

## Protocol-Specific Notes

### MQTT

- Uses Mosquitto broker (must be installed)
- TCP-based, reliable by default
- Higher overhead but guaranteed delivery

### CoAP

- Uses aiocoap library
- UDP-based, REST-like semantics
- Lower overhead, optional reliability

### PRTP

- Custom UDP-based pub/sub protocol
- Q-learning based congestion control
- Adaptive to network conditions
- Lower overhead than MQTT

## Paper Figures

### Recommended Figures

1. **Latency CDF**: Plot cumulative distribution of latencies
2. **Scalability Chart**: Latency vs Node Count line chart
3. **Network Impact Bar Chart**: Performance under different conditions
4. **Overhead Comparison**: Message size/header analysis

### Generating Charts

```python
import matplotlib.pyplot as plt
import json
from pathlib import Path

# Load results
results = json.loads(Path("results/dcoss_benchmark_.../benchmark_report.json").read_text())

# Example: Latency comparison bar chart
protocols = ["mqtt", "coap", "prtp"]
latencies = [results["experiments"]["latency_comparison"]["results"][p]["lat_avg_ms"] 
             for p in protocols]

plt.bar(protocols, latencies)
plt.ylabel("Average Latency (ms)")
plt.title("Protocol Latency Comparison")
plt.savefig("figures/latency_comparison.pdf")
```

## LaTeX Integration

The benchmark automatically generates LaTeX tables. Include in your paper:

```latex
\input{results/dcoss_benchmark_.../latex_tables.tex}
```

Or copy the generated table:

```latex
\begin{table}[htbp]
\caption{End-to-End Latency Comparison (milliseconds)}
\label{tab:latency}
\centering
\begin{tabular}{lcccc}
\hline
\textbf{Protocol} & \textbf{Avg} & \textbf{P50} & \textbf{P95} & \textbf{P99} \\
\hline
MQTT & 12.34 & 10.50 & 25.80 & 45.20 \\
COAP & 8.75 & 7.20 & 18.40 & 32.10 \\
PRTP & 6.50 & 5.80 & 14.20 & 24.50 \\
\hline
\end{tabular}
\end{table}
```

## Troubleshooting

### MQTT Broker Not Running

```bash
sudo systemctl start mosquitto
# or
mosquitto -d
```

### Permission Issues for Network Impairment

Network impairment tests require sudo access to tc (traffic control):

```bash
sudo python run_dcoss_benchmark.py --network
```

### PRTP Binaries Not Found

Build PRTP from source:

```bash
cd ../PRTP_development\ \(Copy\)/PRTP
./configure
make
```

## References

- MQTT: https://mqtt.org/
- CoAP: https://coap.technology/
- PRTP: Internal protocol (PRTP_development/PRTP)
- DCOSS: https://dcoss.org/
