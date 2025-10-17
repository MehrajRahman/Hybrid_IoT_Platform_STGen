# STGen - IoT Protocol Evaluation Testbed

**A lightweight, extensible framework for evaluating IoT protocols with realistic sensor data.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

##  Overview

STGen bridges the gap between network simulators (NS-3, OMNeT++) and physical IoT testbeds by providing:

- **Realistic sensor data generation** (temperature, GPS, motion, camera, etc.)
- **Protocol-agnostic plug-in architecture** for custom protocols
- **Automated test orchestration** with minimal user code
- **Lightweight design** - runs on any laptop without VMs or containers
- **Active & Passive modes** - supports both Python and compiled binaries

##  Features

 Multi-sensor traffic generation with realistic timing patterns  
 Plug-and-play protocol integration  
 Automated metrics collection (latency, throughput, packet loss)  
 Support for C/C++ binaries and Python protocols  
 Reproducible experiments via JSON configs  
 Publication-ready results and plots  

##  Quick Start

### 1. Installation
```bash
git clone https://github.com/MehrajRahman/Hybrid_IoT_Platform_STGen.git
cd STGen
pip install -r requirements.txt
```

### 2. Build C Protocols (Optional)
```bash
chmod +x tools/build_all.sh
./tools/run_all_scenarios.sh
```

### 3. Run Your First Test
```bash
# CoAP example (Python-based)
pip install aiocoap[all]==0.4.7
python -m stgen.main configs/coap.json

# UDP example (C-based)
python -m stgen.main configs/my_udp.json
```

### 4. View Results
```bash
ls results/
python tools/plot_results.py results/coap_1234567890/
```

##  Usage

### Running Tests
```bash
python -m stgen.main <config.json>
```

### Creating Your Own Protocol

1. Copy the template:
```bash
cp -r protocols/template protocols/my_protocol
```

2. Implement the protocol interface in `my_protocol/template.py`

3. Create a config file:
```bash
cp configs/template.json configs/my_protocol.json
```

4. Run:
```bash
python -m stgen.main configs/my_protocol.json
```

See [protocols/template/README.md](protocols/template/README.md) for details.

##  Architecture