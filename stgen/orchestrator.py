# # stgen/orchestrator.py
# """
# Test Orchestration Engine
# Manages protocol lifecycle, data feeding, and metrics collection.
# """

# import importlib
# import json
# import socket
# import time
# import logging
# from pathlib import Path
# from typing import Iterable, Tuple, Dict, Any

# _LOG = logging.getLogger("orchestrator")

# # In _run_active, add node tagging:

# # In save_report:

# class Orchestrator:
#     """
#     Main orchestration engine for STGen.
#     Handles test lifecycle: load → start → feed → measure → stop.
#     """

    
#     def __init__(self, protocol_name: str, cfg: Dict[str, Any]):
#         """
#         Initialize orchestrator with a protocol.
        
#         Args:
#             protocol_name: Name of protocol module in protocols/
#             cfg: Configuration dictionary
#         """
#         self.protocol_name = protocol_name
#         self.cfg = cfg

#         # In Orchestrator.__init__
#         self.node_id = cfg.get("node_id", "unknown")
        
#         # Dynamically import protocol
#         try:
#             mod = importlib.import_module(f"protocols.{protocol_name}")
#             self.protocol = mod.Protocol(cfg)
#         except Exception as e:
#             _LOG.error(f"Failed to load protocol '{protocol_name}'")
#             raise RuntimeError(f"Protocol load error: {e}")
        
#         # Metrics storage
#         self.metrics: Dict[str, Any] = {
#             "sent": 0,
#             "recv": 0,
#             "lat": [],
#             "err": []
#         }
    
#     def run_test(self, stream: Iterable[Tuple[str, Dict, float]]) -> bool:
#         """
#         Execute the full test lifecycle.
        
#         Args:
#             stream: Generator yielding (client_id, data_dict, timeout)
        
#         Returns:
#             bool: True if test completed successfully
#         """
#         _LOG.info(f"Starting test - protocol={self.protocol_name}, mode={self.protocol.mode}")
        
#         # Start server and clients
#         try:
#             self.protocol.start_server()
#             time.sleep(0.5)  # Server bind time
            
#             self.protocol.start_clients(self.cfg["num_clients"])
#             time.sleep(0.5)  # Client connect time
            
#         except Exception as exc:
#             _LOG.exception("Failed to start server/clients")
#             return False
        
#         # Route data based on mode
#         if self.protocol.mode == "active":
#             return self._run_active(stream)
#         else:
#             return self._run_passive()
    
#     def _run_active(self, stream: Iterable[Tuple[str, Dict, float]]) -> bool:
#         """Active mode: orchestrator drives send_data()."""
#         _LOG.info("Running in ACTIVE mode")
        

        
#         for cid, payload, to in stream:
#             if not self.protocol.is_alive():
#                 _LOG.warning("Protocol died mid-test")
#                 break

#             payload["node_id"] = self.node_id
            
#             t0 = time.perf_counter()
            
#             try:
#                 ok, t_srv = self.protocol.send_data(cid, payload)
#             except Exception as e:
#                 self.metrics["err"].append(str(e))
#                 continue
            
#             self.metrics["sent"] += 1
            
#             # Valid latency only if server timestamp is valid
#             if ok and t_srv and t_srv > t0:
#                 self.metrics["lat"].append((t_srv - t0) * 1000)
#                 self.metrics["recv"] += 1
            
#             time.sleep(to)
        
#         return True
    
#     def _run_passive(self) -> bool:
#         """Passive mode: binaries run autonomously."""
#         dur = self.cfg.get("duration", 30)
#         _LOG.info(f"Running in PASSIVE mode for {dur}s")
#         time.sleep(dur)
        
#         # Parse logs written by C binaries
#         self._parse_recv_log()
#         return True
    
#     def _parse_recv_log(self) -> None:
#         """Parse recv.log file written by C server."""
#         log = Path("recv.log")
        
#         if not log.exists():
#             _LOG.warning("recv.log not found - no latency data")
#             return
        
#         for line in log.read_text().splitlines():
#             try:
#                 seq, lat_us = map(int, line.split())
#                 self.metrics["lat"].append(lat_us / 1000.0)  # Convert to ms
#                 self.metrics["recv"] += 1
#             except ValueError:
#                 continue
        
#         # Estimate sent packets
#         self.metrics["sent"] = max(self.metrics["recv"], 1)
#         _LOG.info(f"Parsed {self.metrics['recv']} packets from recv.log")
    
#     def save_report(self, out_dir: Path) -> None:
#         """
#         Generate and save test report.
        
#         Args:
#             out_dir: Output directory for results
#         """
#         out_dir.mkdir(parents=True, exist_ok=True)
        
#         # Calculate statistics
#         lat = sorted(self.metrics["lat"])
        
#         summary = {
#             "protocol": self.cfg["protocol"],
#             "mode": self.protocol.mode,
#             "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
#             "sent": self.metrics["sent"],
#             "recv": self.metrics["recv"],
#             "loss": 1.0 - (self.metrics["recv"] / max(self.metrics["sent"], 1)),
#             "errors": len(self.metrics["err"])
#         }
        
#         if lat:
#             summary["lat_avg_ms"] = sum(lat) / len(lat)
#             summary["lat_min_ms"] = lat[0]
#             summary["lat_max_ms"] = lat[-1]
#             summary["lat_p50_ms"] = lat[len(lat) // 2]
#             summary["lat_p95_ms"] = lat[int(len(lat) * 0.95)]

                
#         summary["node_id"] = self.node_id
#         summary["node_ip"] = socket.gethostname()
        
#         # Save summary
#         (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
        
#         # Save latency log
#         if lat:
#             (out_dir / "latencies.txt").write_text("\n".join(map(str, lat)))
        
#         # Save error log
#         if self.metrics["err"]:
#             (out_dir / "errors.txt").write_text("\n".join(self.metrics["err"]))
        
#         _LOG.info(f"Report saved to {out_dir}/")
#         _LOG.info(f"  Sent: {summary['sent']}, Recv: {summary['recv']}, Loss: {summary['loss']*100:.2f}%")
#         if lat:
#             _LOG.info(f"  Latency: avg={summary['lat_avg_ms']:.2f}ms, p50={summary['lat_p50_ms']:.2f}ms")


# stgen/orchestrator.py
"""
Test Orchestration Engine (Fixed for Distributed Mode)
Manages protocol lifecycle, data feeding, and metrics collection.
"""

import importlib
import json
import socket
import time
import logging
from pathlib import Path
from typing import Iterable, Tuple, Dict, Any

_LOG = logging.getLogger("orchestrator")

class Orchestrator:
    """
    Main orchestration engine for STGen.
    Handles test lifecycle: load → start → feed → measure → stop.
    """
    
    def __init__(self, protocol_name: str, cfg: Dict[str, Any]):
        """
        Initialize orchestrator with a protocol.
        
        Args:
            protocol_name: Name of protocol module in protocols/
            cfg: Configuration dictionary
        """
        self.protocol_name = protocol_name
        self.cfg = cfg
        self.node_id = cfg.get("node_id", "core")
        self.role = cfg.get("role", "core")
        
        # Dynamically import protocol
        try:
            # Try nested structure first: protocols.mqtt.mqtt
            try:
                mod = importlib.import_module(f"protocols.{protocol_name}.{protocol_name}")
            except (ImportError, ModuleNotFoundError):
                # Fall back to flat structure: protocols.mqtt
                mod = importlib.import_module(f"protocols.{protocol_name}")
            
            self.protocol = mod.Protocol(cfg)
        except Exception as e:
            _LOG.error(f"Failed to load protocol '{protocol_name}'")
            raise RuntimeError(f"Protocol load error: {e}")
        
        # Metrics storage
        self.metrics: Dict[str, Any] = {
            "sent": 0,
            "recv": 0,
            "lat": [],
            "err": []
        }
    
    def run_test(self, stream: Iterable[Tuple[str, Dict, float]]) -> bool:
        """
        Execute the full test lifecycle.
        
        Args:
            stream: Generator yielding (client_id, data_dict, timeout)
        
        Returns:
            bool: True if test completed successfully
        """
        _LOG.info(f"Starting test - protocol={self.protocol_name}, mode={self.protocol.mode}, role={self.role}")
        
        # Start server (broker + subscriber)
        try:
            self.protocol.start_server()
            time.sleep(0.5)  # Server bind time
            
            # Only start clients if num_clients > 0
            num_clients = self.cfg.get("num_clients", 0)
            if num_clients > 0:
                _LOG.info(f"Starting {num_clients} clients...")
                self.protocol.start_clients(num_clients)
                time.sleep(0.5)  # Client connect time
            else:
                _LOG.info("Server-only mode - no clients started")
            
        except Exception as exc:
            _LOG.exception("Failed to start server/clients")
            return False
        
        # Route data based on mode
        if self.protocol.mode == "active":
            return self._run_active(stream)
        else:
            return self._run_passive()
    
    def _run_active(self, stream: Iterable[Tuple[str, Dict, float]]) -> bool:
        """Active mode: orchestrator drives send_data()."""
        _LOG.info("Running in ACTIVE mode")
        
        # If this is a server-only node (core), just listen
        if self.cfg.get("num_clients", 0) == 0:
            _LOG.info("Server-only mode - listening for incoming data")
            duration = self.cfg.get("duration", 30)
            _LOG.info(f"Listening for {duration} seconds...")
            time.sleep(duration)
            return True
        
        # Sensor nodes - send data
        for cid, payload, to in stream:
            if not self.protocol.is_alive():
                _LOG.warning("Protocol died mid-test")
                break
            
            # Tag with node ID
            payload["node_id"] = self.node_id
            
            t0 = time.perf_counter()
            
            try:
                ok, t_srv = self.protocol.send_data(cid, payload)
            except Exception as e:
                self.metrics["err"].append(str(e))
                continue
            
            self.metrics["sent"] += 1
            
            # Valid latency only if server timestamp is valid
            if ok and t_srv and t_srv > t0:
                self.metrics["lat"].append((t_srv - t0) * 1000)
                self.metrics["recv"] += 1
            
            time.sleep(to)
        
        return True
    
    def _run_passive(self) -> bool:
        """Passive mode: binaries run autonomously."""
        dur = self.cfg.get("duration", 30)
        _LOG.info(f"Running in PASSIVE mode for {dur}s")
        time.sleep(dur)
        
        # Parse logs written by C binaries
        self._parse_recv_log()
        return True
    
    def _parse_recv_log(self) -> None:
        """Parse recv.log file written by C server."""
        log = Path("recv.log")
        
        if not log.exists():
            _LOG.warning("recv.log not found - no latency data")
            return
        
        for line in log.read_text().splitlines():
            try:
                seq, lat_us = map(int, line.split())
                self.metrics["lat"].append(lat_us / 1000.0)  # Convert to ms
                self.metrics["recv"] += 1
            except ValueError:
                continue
        
        # Estimate sent packets
        self.metrics["sent"] = max(self.metrics["recv"], 1)
        _LOG.info(f"Parsed {self.metrics['recv']} packets from recv.log")
    
    def save_report(self, out_dir: Path) -> None:
        """
        Generate and save test report.
        
        Args:
            out_dir: Output directory for results
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics
        lat = sorted(self.metrics["lat"])
        
        summary = {
            "protocol": self.cfg["protocol"],
            "mode": self.protocol.mode,
            "role": self.role,
            "node_id": self.node_id,
            "node_ip": socket.gethostname(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sent": self.metrics["sent"],
            "recv": self.metrics["recv"],
            "loss": 1.0 - (self.metrics["recv"] / max(self.metrics["sent"], 1)),
            "errors": len(self.metrics["err"])
        }
        
        if lat:
            summary["lat_avg_ms"] = sum(lat) / len(lat)
            summary["lat_min_ms"] = lat[0]
            summary["lat_max_ms"] = lat[-1]
            summary["lat_p50_ms"] = lat[len(lat) // 2]
            summary["lat_p95_ms"] = lat[int(len(lat) * 0.95)]
        
        # Save summary
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
        
        # Save latency log
        if lat:
            (out_dir / "latencies.txt").write_text("\n".join(map(str, lat)))
        
        # Save error log
        if self.metrics["err"]:
            (out_dir / "errors.txt").write_text("\n".join(self.metrics["err"]))
        
        _LOG.info(f"Report saved to {out_dir}/")
        _LOG.info(f"  Sent: {summary['sent']}, Recv: {summary['recv']}, Loss: {summary['loss']*100:.2f}%")
        if lat:
            _LOG.info(f"  Latency: avg={summary['lat_avg_ms']:.2f}ms, p50={summary['lat_p50_ms']:.2f}ms")