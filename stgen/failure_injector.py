# stgen/failure_injector.py
"""
@file failure_injector.py
@brief Failure Injection Framework for STGen
@details Simulates realistic network failures and client crashes to test protocol robustness.
         This module allows STGen to move beyond "happy path" testing by introducing chaotic 
         conditions like packet loss, split-brain partitions, and data corruption.
"""

import random
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# @brief Logger for the failure injector module
_LOG = logging.getLogger("failure_injector")


@dataclass
class FailureEvent:
    """
    @brief Represents a single failure event.
    @details A record of what failure occurred, when, and to whom, used for reporting and analysis.
    """
    time_sec: float  # < Time offset from start when event occurred
    failure_type: str  # < Type: "packet_loss", "client_crash", "network_partition", "corruption"
    # < Client ID affected, or None for global events
    target: Optional[str] = None
    # < Duration of the failure (if applicable)
    duration_sec: Optional[float] = None
    metadata: Dict[str, Any] = None  # < Extra context (e.g., latency amount)


class FailureInjector:
    """
    @brief Injects realistic failures during protocol testing.

    @details Supported failure modes:
             - Packet loss (random or targeted)
             - Client crashes and restarts
             - Network partitions (split-brain)
             - Message corruption
             - Latency spikes
    """

    def __init__(self, cfg: Dict[str, Any]):
        """
        @brief Initialize failure injector.

        @param cfg Configuration dict containing a 'failure_injection' section with keys:
                   - packet_loss: float (0.0-1.0)
                   - client_crashes: List[int] (timestamps in seconds)
                   - network_partition: {start_sec, duration_sec}
                   - message_corruption: float (0.0-1.0)
                   - latency_spike: {probability, duration_ms}
        """
        self.cfg = cfg.get("failure_injection", {})
        self.packet_loss_rate = self.cfg.get("packet_loss", 0.0)
        self.corruption_rate = self.cfg.get("message_corruption", 0.0)

        self.crash_times = self.cfg.get("client_crashes", [])
        self.partition_cfg = self.cfg.get("network_partition", None)
        self.latency_spike_cfg = self.cfg.get("latency_spike", None)

        self.crashed_clients: set[str] = set()
        self.partition_active = False
        self.partition_end_time = 0.0

        self.start_time = time.time()
        self.events: List[FailureEvent] = []

        _LOG.info("Failure Injector initialized: loss=%.1f%%, corruption=%.1f%%",
                  self.packet_loss_rate * 100, self.corruption_rate * 100)

    def should_drop_packet(self, client_id: str) -> bool:
        """
        @brief Determine if a packet should be dropped.

        @details Checks against three conditions:
                 1. Is the specific client currently 'crashed'?
                 2. Is a network partition active and does this client hash to the isolated side?
                 3. Does the random dice roll fall below the configured packet loss rate?

        @param client_id The ID of the client attempting to send.
        @return bool True if the packet should be dropped/ignored.
        """
        elapsed = time.time() - self.start_time

        # Check if client is crashed
        if client_id in self.crashed_clients:
            _LOG.debug(" Packet dropped: client %s crashed", client_id)
            return True

        # Check network partition
        if self.partition_active and time.time() < self.partition_end_time:
            # Partition affects half the clients (simple split-brain)
            if hash(client_id) % 2 == 0:
                _LOG.debug(" Packet dropped: network partition active")
                return True

        # Random packet loss
        if random.random() < self.packet_loss_rate:
            _LOG.debug(" Packet dropped: random loss")
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="packet_loss",
                target=client_id
            ))
            return True

        return False

    def should_corrupt_message(self) -> bool:
        """
        @brief Determine if message should be corrupted.

        @details Randomly decides based on `corruption_rate`.
        @return bool True if message should be corrupted.
        """
        if random.random() < self.corruption_rate:
            elapsed = time.time() - self.start_time
            _LOG.warning("  Message corrupted")
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="corruption"
            ))
            return True
        return False

    def corrupt_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        @brief Corrupt a message payload.

        @details Modifies the payload dictionary in place to simulate data rot.
                 May prefix 'sensor_data' with garbage or scramble the 'seq_no'.

        @param payload The original message dictionary.
        @return Dict[str, Any] The corrupted message dictionary.
        """
        corrupted = payload.copy()

        # Randomly corrupt one field
        if "sensor_data" in corrupted:
            # Flip bits in sensor data
            corrupted["sensor_data"] = "CORRUPTED_" + \
                str(corrupted["sensor_data"])

        if "seq_no" in corrupted and random.random() > 0.5:
            # Corrupt sequence number
            corrupted["seq_no"] = (
                corrupted["seq_no"] + random.randint(-100, 100)) % 65536

        return corrupted

    def check_client_crashes(self) -> List[str]:
        """
        @brief Check if any clients should crash now.

        @details Compares elapsed test time against the configured `crash_times`.
                 If a match is found, a random active client is added to `crashed_clients`.

        @return List[str] List of client IDs that crashed in this check.
        """
        elapsed = time.time() - self.start_time
        crashed_now = []

        for crash_time in self.crash_times:
            if abs(elapsed - crash_time) < 0.5 and crash_time not in [e.time_sec for e in self.events if e.failure_type == "client_crash"]:
                # Time to crash a random client
                client_id = f"client_{random.randint(0, 10)}"
                self.crashed_clients.add(client_id)
                crashed_now.append(client_id)

                _LOG.warning(" Client %s CRASHED at %.1fs", client_id, elapsed)
                self.events.append(FailureEvent(
                    time_sec=elapsed,
                    failure_type="client_crash",
                    target=client_id
                ))

        return crashed_now

    def revive_client(self, client_id: str) -> None:
        """
        @brief Revive a crashed client.

        @details Removes the client from the `crashed_clients` set, allowing it to send again.
        @param client_id Client to revive.
        @return None
        """
        if client_id in self.crashed_clients:
            self.crashed_clients.remove(client_id)
            elapsed = time.time() - self.start_time
            _LOG.info(" Client %s REVIVED at %.1fs", client_id, elapsed)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="client_revive",
                target=client_id
            ))

    def check_network_partition(self) -> bool:
        """
        @brief Check if network partition should be activated.

        @details Manages the lifecycle (start/end) of a network partition based on configuration.
        @return bool True if a partition just started.
        """
        if not self.partition_cfg:
            return False

        elapsed = time.time() - self.start_time
        start_time = self.partition_cfg.get("start_sec", 0)
        duration = self.partition_cfg.get("duration_sec", 10)

        # Check if partition should start
        if not self.partition_active and abs(elapsed - start_time) < 0.5:
            self.partition_active = True
            self.partition_end_time = time.time() + duration
            _LOG.warning(
                "NETWORK PARTITION started at %.1fs (duration: %ds)", elapsed, duration)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="network_partition",
                duration_sec=duration
            ))
            return True

        # Check if partition should end
        if self.partition_active and time.time() >= self.partition_end_time:
            self.partition_active = False
            _LOG.info(" NETWORK PARTITION healed at %.1fs", elapsed)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="partition_healed"
            ))

        return False

    def inject_latency_spike(self) -> Optional[float]:
        """
        @brief Potentially inject artificial latency.

        @details Randomly determines if a thread sleep should be injected to simulate
                 network congestion or processing delays.

        @return Optional[float] Extra delay in seconds, or None if no spike occurred.
        """
        if not self.latency_spike_cfg:
            return None

        probability = self.latency_spike_cfg.get("probability", 0.01)
        duration_ms = self.latency_spike_cfg.get("duration_ms", 500)

        if random.random() < probability:
            elapsed = time.time() - self.start_time
            delay_sec = duration_ms / 1000.0
            _LOG.warning("⏱️  Latency spike: +%.0fms", duration_ms)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="latency_spike",
                metadata={"delay_ms": duration_ms}
            ))
            return delay_sec

        return None

    def get_failure_summary(self) -> Dict[str, Any]:
        """
        @brief Generate summary of all injected failures.

        @details Aggregates counts of each failure type and provides a log of the first 50 events.
        @return Dict[str, Any] Dictionary with failure statistics.
        """
        summary = {
            "total_events": len(self.events),
            "packet_losses": len([e for e in self.events if e.failure_type == "packet_loss"]),
            "corruptions": len([e for e in self.events if e.failure_type == "corruption"]),
            "client_crashes": len([e for e in self.events if e.failure_type == "client_crash"]),
            "network_partitions": len([e for e in self.events if e.failure_type == "network_partition"]),
            "latency_spikes": len([e for e in self.events if e.failure_type == "latency_spike"]),
            "events": [
                {
                    "time_sec": e.time_sec,
                    "type": e.failure_type,
                    "target": e.target,
                    "duration_sec": e.duration_sec
                }
                for e in self.events[:50]  # Limit to first 50 events
            ]
        }

        return summary


# Helper function to enable failure injection in orchestrator
def wrap_send_with_failures(send_func, injector: FailureInjector):
    """
    @brief Wrap protocol send_data() with failure injection.

    @details Creates a decorator-like wrapper that intercepts the `send_data` call.
             It performs failure checks (crashes, drops, corruptions, latency) BEFORE
             calling the actual protocol send function.

    @param send_func The original protocol.send_data method.
    @param injector The initialized FailureInjector instance.

    @return function Wrapped function that matches the signature of send_data but may fail.
    """
    def wrapped_send(client_id: str, data: Dict) -> tuple:
        # Check for crashes
        injector.check_client_crashes()

        # Check for network partition
        injector.check_network_partition()

        # Should drop packet?
        if injector.should_drop_packet(client_id):
            return False, 0.0

        # Corrupt message?
        if injector.should_corrupt_message():
            data = injector.corrupt_payload(data)

        # Inject latency spike?
        spike_delay = injector.inject_latency_spike()
        if spike_delay:
            time.sleep(spike_delay)

        # Actually send
        return send_func(client_id, data)

    return wrapped_send
