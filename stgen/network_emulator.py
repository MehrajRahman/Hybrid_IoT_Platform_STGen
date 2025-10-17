# # stgen/network_emulator.py
# """
# Network condition emulation using Linux tc (traffic control).
# Requires root/sudo privileges.
# """

# import subprocess
# import logging

# _LOG = logging.getLogger("network_emulator")

# class NetworkEmulator:
#     """Emulate network conditions (latency, loss, bandwidth)."""
    
#     def __init__(self, interface: str = "lo"):
#         self.interface = interface
#         self.enabled = False
    
#     def apply_conditions(self, latency_ms: int = 0, loss_pct: float = 0, 
#                         bandwidth_kbps: int = 0, jitter_ms: int = 0):
#         """Apply network conditions using tc."""
#         try:
#             # Clear existing rules
#             subprocess.run(["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"], 
#                           stderr=subprocess.DEVNULL)
            
#             # Build tc command
#             cmd = ["sudo", "tc", "qdisc", "add", "dev", self.interface, "root", "netem"]
            
#             if latency_ms > 0:
#                 cmd.extend(["delay", f"{latency_ms}ms"])
#                 if jitter_ms > 0:
#                     cmd.append(f"{jitter_ms}ms")
            
#             if loss_pct > 0:
#                 cmd.extend(["loss", f"{loss_pct}%"])
            
#             if bandwidth_kbps > 0:
#                 cmd.extend(["rate", f"{bandwidth_kbps}kbit"])
            
#             subprocess.run(cmd, check=True)
#             self.enabled = True
#             _LOG.info(" Network conditions applied: latency=%dms, loss=%.1f%%, bw=%dkbps",
#                      latency_ms, loss_pct, bandwidth_kbps)
#         except Exception as e:
#             _LOG.error("Failed to apply network conditions: %s", e)
    
#     def clear(self):
#         """Remove network emulation."""
#         if self.enabled:
#             subprocess.run(["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
#                           stderr=subprocess.DEVNULL)
#             _LOG.info("Network emulation cleared")



# stgen/network_emulator.py
"""
Network condition emulation with profile support.
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Any

_LOG = logging.getLogger("network_emulator")


class NetworkEmulator:
    """Apply realistic network conditions from JSON profiles."""
    
    def __init__(self, interface: str = "eth0"):
        self.interface = interface
        self.enabled = False
        self.profile_name = None
    
    @classmethod
    def from_profile(cls, profile_path: str, interface: str = "eth0"):
        """Load network conditions from profile file."""
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
        """Apply network conditions using tc."""
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
        """Remove network emulation."""
        if self.enabled:
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                stderr=subprocess.DEVNULL
            )
            _LOG.info("Network emulation cleared")