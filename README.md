# STGen - IoT Protocol Evaluation Testbed

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/MehrajRahman/Hybrid_IoT_Platform_STGen)

**A lightweight, extensible framework for evaluating IoT communication protocols with realistic sensor data and network conditions.**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Supported Protocols](#-supported-protocols)
- [Testing Scenarios](#-testing-scenarios)
- [Results & Metrics](#-results--metrics)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## 🎯 Overview

**STGen** (Sensor Traffic Generator) bridges the gap between network simulators and physical IoT testbeds by providing a **realistic, reproducible, and lightweight** protocol testing environment. It enables researchers and developers to:

- **Validate custom IoT protocols** under realistic workloads
- **Compare protocol performance** side-by-side with automated metrics
- **Generate readymade results** with minimal configuration

Unlike traditional simulators, STGen:
- ✅ Runs on any laptop without any containers
- ✅ Supports both Python and compiled C/C++ protocol implementations
- ✅ Provides realistic multi-sensor traffic patterns
- ✅ Offers distributed testing across multiple physical nodes

---

## ✨ Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| 🔌 **Protocol-Agnostic Architecture** | Plug-and-play integration for any IoT protocol (MQTT, CoAP, custom UDP, etc.) |
| 📊 **Realistic Sensor Simulation** | 7+ sensor types (temperature, GPS, motion, camera, etc.) with configurable timing patterns |
| 🌐 **Network Emulation** | Built-in network condition profiles (WiFi, 4G, LoRaWAN, congested networks) |
| 💥 **Failure Injection** | Test resilience under packet loss, crashes, network partitions, and Byzantine failures |
| 📈 **Automated Metrics Collection** | Latency, throughput, packet loss, energy consumption, and QoS compliance |
| 🔄 **Protocol Comparison** | Side-by-side performance analysis with automated report generation |
| 🖥️ **Distributed Testing** | Multi-node deployment for real-world network topology testing |
| 📦 **Binary Support** | Works with both Python implementations and compiled C/C++ binaries |
| 🎨 **Publication-Ready Output** | Automated graphs, tables, and LaTeX-compatible results |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        STGen Framework                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Sensor     │───▶│  Protocol    │───▶│   Metrics    │      │
│  │  Generator   │    │  Interface   │    │  Collector   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Network    │    │   Failure    │    │    Report    │      │
│  │  Emulator    │    │  Injector    │    │  Generator   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Your Protocol   │
                    │  (MQTT/CoAP/     │
                    │   Custom/etc.)   │
                    └──────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- **Python**
- **Operating System**: Linux, macOS
- **Optional**: GCC/G++ for compiling C/C++ protocol implementations

### Standard Installation for COAP & MQTT

```bash
# --- 1. Setup & Environment ---
# Clone and enter directory immediately
git clone https://github.com/MehrajRahman/Hybrid_IoT_Platform_STGen.git
cd Hybrid_IoT_Platform_STGen

# Create and activate virtual environment
python3 -m venv env
source env/bin/activate  # Windows PowerShell: .\env\Scripts\activate

# --- 2. System Dependencies (Broker) ---
# NOTE: For a cleaner setup, consider running Mosquitto via Docker instead of installing it on the host.
# Linux/WSL (Debian/Ubuntu specific):
sudo apt update -q && sudo apt install -y mosquitto
sudo systemctl enable --now mosquitto
systemctl is-active mosquitto # Verify status without verbose output

# --- 3. Python Dependencies ---
# Upgrade pip first to avoid wheel build errors, then install packages
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# --- 4. Execution ---
# Simulate single protocol (Fixed double-space typo)
python3 -m stgen.main --scenario smart_agriculture --protocol coap

# Compare multiple protocols
python3 -m stgen.main --compare coap,mqtt --scenario smart_agriculture
```

### Protocol-Specific Dependencies

#### For MQTT Protocol
```bash
# Linux/macOS
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Or use the installation script
chmod +x tools/install_mqtt.sh
./tools/install_mqtt.sh
```

#### For CoAP Protocol
```bash
pip install aiocoap[all]==0.4.7

# Or use the installation script
chmod +x tools/install_coap.sh
./tools/install_coap.sh
```

### Building C/C++ Protocols (Optional)

```bash
# Build all C/C++ protocol implementations
chmod +x tools/build_all.sh
./tools/build_all.sh
```



---

## ⚙️ Configuration

### Configuration File Structure

```json
{
  "protocol": "mqtt",
  "mode": "active",
  "server_ip": "127.0.0.1",
  "server_port": 1883,
  "num_clients": 4,
  "duration": 60,
  "sensors": ["temp", "humidity", "motion", "light"],
  "network_profile": "wifi",
  "weibull_k": 0.8,
  "weibull_scale": 2.0,
  "use_weibull_iat": true,
  "packets_per_client": 100,
  "failure_injection": {
    "enabled": true,
    "packet_loss": 0.05,
    "crash_probability": 0.01
  }
}
```

### Configuration Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `protocol` | string | Protocol name (must match folder in `protocols/`) | **Required** |
| `mode` | string | `"active"` (Python) or `"passive"` (C/C++ binary) | `"active"` |
| `server_ip` | string | Server/broker IP address | `"127.0.0.1"` |
| `server_port` | integer | Server/broker port | Protocol-specific |
| `num_clients` | integer | Number of simulated clients/publishers | `4` |
| `duration` | integer | Test duration in seconds | `60` |
| `sensors` | array | List of sensor types to simulate | `["temp"]` |
| `network_profile` | string | Network condition profile name | `null` |
| `weibull_k` | float | Weibull shape parameter for inter-arrival times | `0.8` |
| `weibull_scale` | float | Weibull scale parameter | `2.0` |
| `use_weibull_iat` | boolean | Use Weibull distribution for realistic timing | `true` |
| `packets_per_client` | integer | Packets per client (if not duration-based) | `null` |

---

### Adding New Protocols

See [Custom Protocol Integration](#custom-protocol-integration) section above.

---

## 🎬 Testing Scenarios

STGen includes pre-configured scenarios for common IoT use cases:

### Available Scenarios

| Scenario | Description | Sensors | Duration | Use Case |
|----------|-------------|---------|----------|----------|
| **Smart Home** | Residential IoT devices | temp, humidity, motion, light | 300s | Home automation |
| **Industrial IoT** | Factory monitoring | temp, vibration, pressure | 600s | Manufacturing |
| **Healthcare Wearables** | Medical sensors | heart_rate, spo2, temp | 300s | Patient monitoring |
| **Smart Agriculture** | Farm sensors | soil_moisture, temp, humidity | 900s | Precision farming |
| **Stress Test** | High-load testing | All sensors | 120s | Performance limits |
| **Intermittent Connectivity** | Unreliable networks | temp, gps | 600s | Mobile/remote IoT |

### Using Scenarios

```bash
# List available scenarios
python -m stgen.main --list-scenarios

# Run with a specific scenario
python -m stgen.main --scenario smart_home --protocol mqtt

# Compare protocols on a scenario
python -m stgen.main --compare coap,mqtt --scenario industrial_iot
```

### Scenario Configuration Files

Located in `context_configurations/`:
- `smart_home.json`
- `industrial_iot.json`
- `healthcare_wearables.json`
- `intermittent_connectivity.json`
- `stress_test.json`

---


### Using Network Profiles

In your configuration file:

```json
{
  "protocol": "mqtt",
  "network_profile": "wifi",
  ...
}
```

### Custom Network Profiles

Create custom profiles in `configs/network_conditions/`:

```json
{
  "name": "my_custom_network",
  "latency_ms": 30,
  "jitter_ms": 10,
  "packet_loss": 0.03,
  "bandwidth_kbps": 5000
}
```

---

## 📊 Results & Metrics

### Collected Metrics

STGen automatically collects comprehensive performance metrics:

#### Latency Metrics
- End-to-end latency (min, max, mean, median, p95, p99)
- Per-sensor latency breakdown
- Latency distribution histograms

#### Throughput Metrics
- Messages per second
- Bytes per second
- Per-client throughput

#### Reliability Metrics
- Packet delivery ratio (PDR)
- Packet loss rate
- Out-of-order delivery rate

#### Energy Metrics
- Estimated energy consumption
- Energy per message
- Power consumption over time


### Example Summary Output

```json
{
  "protocol": "mqtt",
  "duration": 60,
  "total_messages": 2400,
  "latency": {
    "mean_ms": 12.5,
    "median_ms": 10.2,
    "p95_ms": 25.3,
    "p99_ms": 45.7
  },
  "throughput": {
    "messages_per_sec": 40.0,
    "bytes_per_sec": 3200
  },
  "reliability": {
    "packet_delivery_ratio": 0.98,
    "packet_loss_rate": 0.02
  },
  "energy": {
    "total_joules": 150.5,
    "joules_per_message": 0.063
  }
}
```

---



### Batch Testing

Run multiple tests automatically:

```bash
# Run all scenarios for a protocol

# Run all protocols for a scenario

```

---

## 📁 Project Structure

```
Hybrid_IoT_Platform_STGen/
├── configs/                          # Configuration files
│   ├── scenarios/                    # Scenario definitions
│   ├── network_conditions/           # Network profiles
│   ├── coap.json                     # CoAP config
│   ├── mqtt.json                     # MQTT config
│   ├── srtp.json                     # SRTP config
│   └── template.json                 # Template config
│
├── context_configurations/           # Pre-built scenario configs
│   ├── smart_home.json
│   ├── industrial_iot.json
│   ├── healthcare_wearables.json
│   ├── intermittent_connectivity.json
│   └── stress_test.json
│
├── protocols/                        # Protocol implementations
│   ├── coap/                         # CoAP protocol
│   ├── mqtt/                         # MQTT protocol
│   ├── SRTP/                         # SRTP protocol (C binary)
│   ├── my_udp/                       # Custom UDP
│   └── template/                     # Template for new protocols
│
├── stgen/                            # Core framework
│   ├── main.py                       # CLI entry point
│   ├── orchestrator.py               # Test orchestration
│   ├── protocol_interface.py         # Protocol abstraction
│   ├── sensor_generator.py           # Sensor data generation
│   ├── metrics_collector.py          # Metrics collection
│   ├── failure_injector.py           # Failure injection
│   ├── network_emulator.py           # Network emulation
│   ├── report_generator.py           # Report generation
│   ├── comparator.py                 # Protocol comparison
│   ├── validator.py                  # QoS validation
│   ├── energy_model.py               # Energy estimation
│   └── utils.py                      # Utility functions
│
├── distributed/                      # Distributed testing
│   ├── core_node.py                  # Core/broker node
│   ├── sensor_node.py                # Sensor/publisher node
│   ├── query_client.py               # Query/consumer node
│   └── aggregate_results.py          # Results aggregation
│
├── tools/                            # Utility scripts
│   ├── build_all.sh                  # Build C/C++ protocols
│   ├── install_mqtt.sh               # Install MQTT broker
│   ├── install_coap.sh               # Install CoAP dependencies
│   ├── run_all_scenarios.sh          # Batch testing
│   ├── plot_results.py               # Generate plots
│   └── generate_graphs.py            # Graph generation
│
├── results/                          # Test results (generated)
│   ├── <protocol>_<timestamp>/
│   └── comparisons/
│
├── tests/                            # Unit tests
│   └── test_orchestrator.py
│
├── requirements.txt                  # Python dependencies
├── setup.py                          # Package setup
├── LICENSE                           # MIT License
└── README.md                         # This file
```

---

## Contributing Guidelines

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-new-feature`
3. **Make your changes** and add tests
4. **Run tests**: `pytest tests/`
5. **Commit your changes**: `git commit -am 'Add new feature'`
6. **Push to the branch**: `git push origin feature/my-new-feature`
7. **Submit a Pull Request**

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 MehrajRahman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

**[⬆ Back to Top](#stgen---iot-protocol-evaluation-testbed)**

Made By DHMAINetRG

</div>