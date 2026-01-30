# PRTP Protocol Adapter for STGen

## Overview

PRTP (Publish/Subscribe Real-Time Protocol) is an IoT protocol designed for efficient sensor data distribution. This adapter integrates PRTP with STGen for benchmarking against MQTT and CoAP.

## Key Features

- **UDP-based transport**: Lower overhead than TCP-based protocols
- **Publish/Subscribe pattern**: Efficient multicast-style distribution
- **Reliable/Unreliable modes**: Configurable delivery guarantees
- **Q-Learning congestion control**: Adaptive to network conditions
- **BSON serialization**: Efficient binary encoding
- **Fragmentation support**: Large payload handling

## Architecture

```
                    ┌─────────────────┐
   Sensors ──UDP──► │  PRTP Server    │ ──UDP──► Subscribed Clients
  (port 5000)       │ (Q-Learning CC) │        (port 5001)
                    └─────────────────┘
```

## Modes

### Active Mode (Default)
Python implementation with direct UDP communication. Best for benchmarking as it allows precise latency measurement.

```json
{
  "protocol": "prtp",
  "mode": "active",
  "use_c_binaries": false
}
```

### Passive Mode (C Binaries)
Uses compiled PRTP_server and PRTP_client binaries. Better performance but less metric visibility.

```json
{
  "protocol": "prtp",
  "mode": "passive",
  "use_c_binaries": true,
  "prtp_bin_path": "/path/to/PRTP/application"
}
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `server_ip` | string | "127.0.0.1" | Server bind address |
| `server_port` | int | 5001 | Client subscription port |
| `sensor_port` | int | 5000 | Sensor data receive port |
| `reliable` | bool | false | Enable reliable delivery |
| `q_learning_enabled` | bool | true | Enable Q-learning congestion control |
| `use_c_binaries` | bool | false | Use compiled C binaries |
| `prtp_bin_path` | string | auto | Path to PRTP binaries |

## Building C Binaries

If using passive mode with C binaries:

```bash
cd PRTP_development/PRTP
./configure
make
```

This creates:
- `application/PRTP_server` - Server binary
- `application/PRTP_client` - Client binary

## Protocol Comparison Notes

### PRTP vs MQTT
- PRTP uses UDP vs MQTT's TCP
- Lower latency, but potentially higher loss without reliability
- Simpler architecture (no external broker required)
- Q-learning provides adaptive congestion control

### PRTP vs CoAP
- Both use UDP
- PRTP is publish/subscribe vs CoAP's REST-like model
- PRTP has built-in multicast support
- Different reliability mechanisms (PRTP ACK/NACK vs CoAP Confirmable)

## Usage with STGen

```python
from stgen.comparator import ProtocolComparator

comparator = ProtocolComparator(
    "scenario.json",
    protocols=["mqtt", "coap", "prtp"]
)
results = comparator.run_comparison()
```

## Metrics Collected

- **Latency**: Round-trip time for reliable mode
- **Throughput**: Messages per second
- **Loss Rate**: Percentage of dropped packets
- **Jitter**: Latency variation

## References

- PRTP Source: `PRTP_development/PRTP/`
- Protocol Specification: `docs/spec-beams/`
- Q-Learning Agent: `src/q_agent.c`
