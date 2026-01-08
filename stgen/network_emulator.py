# stgen/network_emulator.py
"""
@file network_emulator.py
@brief Network condition emulation with profile support.
@details Provides an interface to the Linux Traffic Control (tc) subsystem to emulate
         network impairments like latency, jitter, packet loss, and bandwidth limits.
         Requires root privileges (sudo) or CAP_NET_ADMIN capabilities.
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Any

## @brief Logger for the network emulator module
_LOG = logging.getLogger("network_emulator")


class NetworkEmulator:
    """
    @brief Apply realistic network conditions from JSON profiles.
    @details Wraps the Linux 'tc' (Traffic Control) command to apply 'netem' (Network Emulation)
             rules to a specific network interface. This allows testing protocols under
             adverse conditions.
    """
    
    def __init__(self, interface: str = "eth0"):
        """
        @brief Initialize the Network Emulator.
        
        @param interface The network interface to apply rules to (e.g., 'eth0', 'lo'). 
                         Defaults to "eth0".
        """
        self.interface = interface
        self.enabled = False
        self.profile_name = None
    
    @classmethod
    def from_profile(cls, profile_path: str, interface: str = "eth0"):
        """
        @brief Load network conditions from a JSON profile file.
        
        @details Reads a JSON file containing keys for latency, jitter, loss, and bandwidth,
                 then creates an instance and immediately applies those conditions.
        
        @param cls The class type.
        @param profile_path Path to the JSON profile file.
        @param interface The network interface to use.
        @return NetworkEmulator An initialized instance with conditions applied.
        """
        emulator = cls(interface)
        profile = json.loads(Path(profile_path).read_text())
        
        emulator.apply_conditions(
            latency_ms=profile.get("latency_ms", 0),
            jitter_ms=profile.get("jitter_ms", 0),
            loss_pct=profile.get("loss_percent", 0),
            bandwidth_kbps=profile.get("bandwidth_kbps", 0)
        )
        
        emulator.profile_name = profile.get("name", "Unknown")
        _LOG.info("Applied profile: %s", emulator.profile_name)
        
        return emulator
    
    def apply_conditions(self, latency_ms: int = 0, jitter_ms: int = 0,
                         loss_pct: float = 0, bandwidth_kbps: int = 0):
        """
        @brief Apply network conditions using the 'tc' command.
        
        @details Constructs and executes a `tc qdisc add ... netem` command.
                 It first clears any existing rules on the root qdisc of the interface.
                 
        @warning This method executes shell commands using `sudo`.
        
        @param latency_ms Base latency in milliseconds.
        @param jitter_ms Latency variation (jitter) in milliseconds.
        @param loss_pct Packet loss percentage (0.0 to 100.0).
        @param bandwidth_kbps Bandwidth limit in kilobits per second.
        @return None
        """
        try:
            # Clear existing rules
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                stderr=subprocess.DEVNULL
            )
            
            # Build tc command
            cmd = ["sudo", "tc", "qdisc", "add", "dev", self.interface, "root", "netem"]
            
            if latency_ms > 0:
                cmd.extend(["delay", f"{latency_ms}ms"])
                if jitter_ms > 0:
                    cmd.append(f"{jitter_ms}ms")
            
            if loss_pct > 0:
                cmd.extend(["loss", f"{loss_pct}%"])
            
            if bandwidth_kbps > 0:
                cmd.extend(["rate", f"{bandwidth_kbps}kbit"])
            
            subprocess.run(cmd, check=True)
            self.enabled = True
            
            _LOG.info(" Network conditions: latency=%dms±%dms, loss=%.1f%%, bw=%dkbps",
                      latency_ms, jitter_ms, loss_pct, bandwidth_kbps)
        except subprocess.CalledProcessError as e:
            _LOG.error("Failed to apply network conditions: %s", e)
            _LOG.error("Make sure you run with sudo or have CAP_NET_ADMIN")
    
    def clear(self):
        """
        @brief Remove network emulation rules.
        
        @details Deletes the root qdisc from the interface, effectively resetting 
                 it to default behavior.
        
        @return None
        """
        if self.enabled:
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                stderr=subprocess.DEVNULL
            )
            _LOG.info("Network emulation cleared")