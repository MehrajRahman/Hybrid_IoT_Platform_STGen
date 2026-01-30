#!/usr/bin/env python3
"""
PRTP (PRIoTP - Partial-Reliable Internet of Things Protocol) Plugin for STGen

PRTP is a publish-subscribe IoT protocol with the following architecture:

    Sensors ──UDP──► PRTP_server ──UDP──► Subscribed Clients
           (sensor_port)        (client_port)

Key components:
1. PRTP_server: Receives sensor data and distributes to subscribed clients
2. Sensors: Generate and send data to the server (sensor.py)
3. PRTP_client: Subscribes to receive updates from the server

This adapter uses the compiled C binaries for proper benchmarking.

Reference: PRTP_development/PRTP/ and launcher/
"""

import json
import logging
import os
import platform
import random
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface

_LOG = logging.getLogger("prtp")

# PRTP Default Ports (from PRTP source)
PRTP_SENSOR_PORT = 5000   # Sensors send data here
PRTP_CLIENT_PORT = 5001   # Clients subscribe here
PRTP_MTU = 1300


class SensorSimulator:
    """
    Python sensor simulator that sends data to PRTP server.
    Replicates the behavior of launcher/sensor.py
    """
    
    def __init__(self, sensor_id: str, sensor_type: str, server_ip: str, 
                 server_port: int, rate_hz: float = 1.0):
        self.sensor_id = f"{sensor_type}_{sensor_id}"
        self.sensor_type = sensor_type
        self.server_ip = server_ip
        self.server_port = server_port
        self.rate_hz = rate_hz
        self.seq_no = 0
        self._alive = True
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        
        # Metrics
        self.messages_sent = 0
        self.send_times: List[float] = []
    
    def start(self):
        """Start sensor simulation in background thread."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        _LOG.debug("Sensor %s started", self.sensor_id)
    
    def stop(self):
        """Stop sensor simulation."""
        self._alive = False
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
        if self._thread:
            self._thread.join(timeout=2)
    
    def send_once(self, data: Dict = None) -> Tuple[bool, float]:
        """
        Send a single sensor message and return (success, send_time).
        For active mode integration.
        """
        try:
            with self._lock:
                self.seq_no += 1
                seq = self.seq_no
            
            curr_time = round(time.time(), 3)
            
            # Generate sensor value based on type
            if data and "sensor_data" in data:
                val = data["sensor_data"]
            else:
                val = self._generate_value()
            
            # Format message exactly like launcher/sensor.py
            message = {
                "dev_id": str(self.sensor_id),
                "ts": str(curr_time),
                "seq_no": str(seq),
                "data_size": str(len(str(val))),
                "sensor_data": str(val)
            }
            
            send_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                payload = str(message).encode('utf-8')
                sock.sendto(payload, (self.server_ip, self.server_port))
                self.messages_sent += 1
                self.send_times.append(send_time)
                return True, send_time
            finally:
                sock.close()
                
        except Exception as e:
            _LOG.warning("Sensor %s send error: %s", self.sensor_id, e)
            return False, 0.0
    
    def _run_loop(self):
        """Background sending loop."""
        interval = 1.0 / self.rate_hz if self.rate_hz > 0 else 1.0
        
        while self._alive:
            self.send_once()
            time.sleep(interval)
    
    def _generate_value(self) -> str:
        """Generate sensor value based on type."""
        import random
        
        if self.sensor_type == "temp":
            return f"{round(random.uniform(15, 35), 1)} C"
        elif self.sensor_type == "humidity":
            return f"{round(random.uniform(30, 80), 1)}%"
        elif self.sensor_type == "device":
            return random.choice(["ON", "OFF"])
        elif self.sensor_type == "motion":
            return random.choice(["DETECTED", "CLEAR"])
        else:
            return f"{random.randint(0, 100)}"


class PRTPClientWrapper:
    """
    Wrapper for PRTP_client binary that tracks received messages.
    
    NOTE: PRTP_client creates logs in a directory relative to its CWD.
    The -l flag specifies the log directory name (not absolute path).
    Logs go to: <CWD>/<log_dir_name>/<sensor_id>.log
    
    FIX: We now use absolute paths and ensure the log directory is created
    in a known location that STGen can find.
    """
    
    def __init__(self, client_id: int, server_ip: str, server_port: int,
                 prtp_bin_path: Path, log_dir: Path):
        self.client_id = client_id
        self.server_ip = server_ip
        self.server_port = server_port
        self.prtp_bin_path = prtp_bin_path
        
        # FIX: Use the provided log_dir as the base, create client-specific subdirectory
        # This ensures STGen knows exactly where to find the logs
        self.log_dir_name = f"client{client_id}_sensor_log"
        self.log_dir = log_dir / self.log_dir_name  # Use provided log_dir base!
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.process: Optional[subprocess.Popen] = None
        
        # Metrics (read from log files after test)
        self.messages_received = 0
        self.receive_times: Dict[str, List[Tuple[float, int, str]]] = {}  # sensor_id -> [(timestamp, seq, data)]
    
    def start(self, subscribe_all: bool = True):
        """Start PRTP_client process."""
        exe = self.prtp_bin_path / "PRTP_client"
        
        if not exe.exists():
            raise FileNotFoundError(f"PRTP_client not found at {exe}")
        
        # Clean old logs - handle permission errors gracefully
        if self.log_dir.exists():
            import shutil
            try:
                shutil.rmtree(self.log_dir)
            except PermissionError:
                _LOG.warning("Could not clean old log dir %s (permission denied), trying with sudo", self.log_dir)
                try:
                    subprocess.run(["sudo", "-n", "rm", "-rf", str(self.log_dir)], 
                                   capture_output=True, timeout=5)
                except Exception:
                    _LOG.warning("Could not clean log dir even with sudo, continuing anyway")
        
        # Recreate log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # FIX: Use ABSOLUTE path for -l flag so logs go to known location
        # PRTP_client will chdir to this directory for logging
        absolute_log_dir = str(self.log_dir.resolve())
        
        cmd = [
            str(exe),
            f"-l{absolute_log_dir}",  # FIX: Use absolute path!
            f"-s{self.server_ip}",
            f"-p{self.server_port}",
        ]
        
        if subscribe_all:
            cmd.append("-A")  # Subscribe to all sensors with reliability
        
        _LOG.info("Starting PRTP_client %d: %s", self.client_id, ' '.join(cmd))
        _LOG.info("  Log directory: %s", absolute_log_dir)
        
        try:
            # IMPORTANT: Do NOT use preexec_fn=os.setsid for clients!
            # This prevents SIGINT from being delivered properly, resulting in empty log files.
            # We need direct SIGINT to the process for graceful shutdown with log flush.
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.prtp_bin_path),  # Set CWD to PRTP application dir for binary dependencies
            )
        except Exception as e:
            _LOG.error("Failed to start PRTP_client %d: %s", self.client_id, e)
            raise
    
    def stop(self):
        """
        Stop PRTP_client process.
        
        IMPORTANT: Use SIGINT for graceful shutdown to ensure log files are flushed!
        SIGTERM/SIGKILL will result in empty log files.
        """
        if self.process and self.process.poll() is None:
            try:
                _LOG.debug("Sending SIGINT to PRTP_client %d (PID %d)", 
                          self.client_id, self.process.pid)
                
                # Use SIGINT directly to process (not process group) for graceful shutdown
                # This ensures log buffers are flushed properly
                os.kill(self.process.pid, signal.SIGINT)
                
                # Wait longer for graceful shutdown and log flush
                for _ in range(20):  # Wait up to 2 seconds
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                if self.process.poll() is None:
                    _LOG.warning("Client %d didn't respond to SIGINT, sending SIGTERM", self.client_id)
                    os.kill(self.process.pid, signal.SIGTERM)
                    time.sleep(0.5)
                    
                if self.process.poll() is None:
                    _LOG.warning("Client %d didn't respond to SIGTERM, sending SIGKILL", self.client_id)
                    os.kill(self.process.pid, signal.SIGKILL)
                    
                exit_code = self.process.poll()
                _LOG.debug("PRTP_client %d stopped with exit code %s", self.client_id, exit_code)
                
            except Exception as e:
                _LOG.warning("Error stopping client %d: %s", self.client_id, e)
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect metrics from client log files.
        
        PRTP_client log format: <receive_timestamp>  <seq_no>  <data>
        Example: 1768928884.36   0       7.0 C
        
        These are REAL receive timestamps from the client!
        """
        metrics = {
            "client_id": self.client_id,
            "messages_received": 0,
            "log_files": [],
            "receive_times": {}  # sensor_id -> [(timestamp, seq, data)]
        }
        
        _LOG.info("Collecting metrics for client %d from: %s", self.client_id, self.log_dir)
        
        if not self.log_dir.exists():
            _LOG.warning("Client log dir does not exist: %s", self.log_dir)
            # Try to list parent directory to see what's there
            parent = self.log_dir.parent
            if parent.exists():
                _LOG.warning("  Parent dir contents: %s", list(parent.iterdir()))
            return metrics
        
        # List all files in log directory
        all_files = list(self.log_dir.iterdir())
        _LOG.info("  Found %d files in log dir: %s", len(all_files), [f.name for f in all_files])
        
        # Parse messages from log files - format: <timestamp> <seq_no> <data>
        for log_file in self.log_dir.glob("*.log"):
            try:
                # Extract sensor_id from filename (e.g., temp_1.log -> temp_1)
                sensor_id = log_file.stem
                
                # Check file size
                file_size = log_file.stat().st_size
                _LOG.info("  Processing %s (size: %d bytes)", log_file.name, file_size)
                
                if file_size == 0:
                    _LOG.warning("  Log file is empty: %s", log_file.name)
                    continue
                
                entries = []
                with open(log_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse: <timestamp>  <seq_no>  <data>
                        parts = line.split(None, 2)  # Split on whitespace, max 3 parts
                        if len(parts) >= 2:
                            try:
                                timestamp = float(parts[0])
                                seq_no = int(parts[1])
                                data = parts[2] if len(parts) > 2 else ""
                                entries.append((timestamp, seq_no, data))
                                metrics["messages_received"] += 1
                            except ValueError as e:
                                _LOG.debug("Skipping malformed log line: %s", line)
                                continue
                
                self.receive_times[sensor_id] = entries
                metrics["receive_times"][sensor_id] = entries
                metrics["log_files"].append(str(log_file))
                
                _LOG.debug("Parsed %d messages from %s", len(entries), log_file.name)
                
            except Exception as e:
                _LOG.warning("Error reading log %s: %s", log_file, e)
        
        self.messages_received = metrics["messages_received"]
        _LOG.info("Client %d: received %d messages from %d sensors", 
                  self.client_id, metrics["messages_received"], len(metrics["receive_times"]))
        
        return metrics


class Protocol(ProtocolInterface):
    """
    PRTP Protocol Adapter for STGen.
    
    Uses the actual PRTP C binaries for accurate benchmarking:
    - PRTP_server: Receives sensor data and distributes to subscribed clients
    - PRTP_client: Subscribes to receive sensor updates
    - sensor.py: Python sensors that send data to server
    """
    
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        
        # Configuration
        self.server_ip = cfg.get("server_ip", "127.0.0.1")
        # PRTP uses two ports:
        # - sensor_port: where sensors send data TO the server
        # - client_port: where clients subscribe to receive FROM the server
        base_port = cfg.get("server_port", PRTP_SENSOR_PORT)
        self.sensor_port = cfg.get("sensor_port", base_port)
        self.client_port = cfg.get("client_port", base_port + 1)  # Default: sensor_port + 1
        self.mode = cfg.get("mode", "active")
        
        # RTT measurement mode:
        # - "one_way": Measure sensor→server→client (one direction, original behavior)
        # - "rtt_approx": Double one-way latency as RTT approximation
        # - "rtt": Synonym for "rtt_approx" for convenience
        self.latency_mode = cfg.get("latency_mode", "rtt_approx")  # Default to RTT for fair comparison
        _LOG.info("  Latency mode: %s", self.latency_mode)
        
        # Find PRTP binaries
        self.prtp_path = self._find_prtp_path(cfg.get("prtp_bin_path"))
        self.launcher_path = self._find_launcher_path()
        
        # Runtime state
        self._alive = True
        self._server_process: Optional[subprocess.Popen] = None
        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._sensors: List[SensorSimulator] = []
        self._clients: List[PRTPClientWrapper] = []
        self._processes: List[subprocess.Popen] = []
        
        # Metrics
        self._msg_count = 0
        self._recv_count = 0
        self._lat: List[float] = []
        self._send_times: Dict[Tuple[str, int], float] = {}  # (sensor_id, seq_no) -> send_time
        
        # Log directory for this test
        self._log_base = Path("./prtp_logs") / f"test_{int(time.time())}"
        self._log_base.mkdir(parents=True, exist_ok=True)
        
        _LOG.info("PRTP Protocol initialized")
        _LOG.info("  PRTP binaries: %s", self.prtp_path)
        _LOG.info("  Sensor port: %d, Client port: %d", self.sensor_port, self.client_port)
    
    def _cleanup_existing_prtp_processes(self) -> None:
        """
        Kill any existing PRTP_server or PRTP_client processes.
        This prevents 'Address already in use' errors when restarting tests.
        """
        import subprocess
        
        for proc_name in ["PRTP_server", "PRTP_client"]:
            try:
                # Try regular pkill first
                subprocess.run(
                    ["pkill", "-9", "-f", proc_name],
                    capture_output=True,
                    timeout=2
                )
            except Exception:
                pass
            
            try:
                # Also try with sudo if running as root
                subprocess.run(
                    ["sudo", "-n", "pkill", "-9", "-f", proc_name],
                    capture_output=True,
                    timeout=2
                )
            except Exception:
                pass
        
        # Brief wait for ports to be released
        time.sleep(0.3)
    
    def _find_prtp_path(self, explicit_path: str = None) -> Path:
        """Find PRTP binary directory."""
        if explicit_path:
            path = Path(explicit_path)
            if path.exists():
                return path
        
        candidates = [
            Path(__file__).parent.parent.parent.parent / "PRTP_development (Copy)" / "PRTP" / "application",
            Path.home() / "PRTP" / "application",
            Path("/opt/PRTP/application"),
        ]
        
        for path in candidates:
            if (path / "PRTP_server").exists():
                return path
        
        _LOG.warning("PRTP binaries not found, using Python-only mode")
        return None
    
    def _find_launcher_path(self) -> Path:
        """Find launcher directory with sensor.py."""
        candidates = [
            Path(__file__).parent.parent.parent.parent / "PRTP_development (Copy)" / "launcher",
            Path(__file__).parent.parent.parent.parent / "PRTP_development (Copy)" / "PRTP" / "application",
        ]
        
        for path in candidates:
            if (path / "sensor.py").exists():
                return path
        
        return None
    
    # =========================================================================
    # ProtocolInterface Implementation
    # =========================================================================
    
    def start_server(self, num_sensors: int = None) -> None:
        """
        Start PRTP_server process.
        
        Args:
            num_sensors: Number of sensors to register. If None, uses config.
        """
        if not self.prtp_path or not (self.prtp_path / "PRTP_server").exists():
            _LOG.warning("PRTP_server binary not found, using Python stub")
            self._start_python_server_stub()
            return
        
        # FIX: Clean up any existing PRTP processes to avoid "Address in use" errors
        _LOG.debug("Cleaning up existing PRTP processes...")
        self._cleanup_existing_prtp_processes()
        
        _LOG.info("Starting PRTP_server...")
        
        # Determine number of sensors from config if not specified
        if num_sensors is None:
            num_sensors = self.cfg.get("num_clients", 4)
        
        # FIX: Create sensor.list file with ABSOLUTE path (required by PRTP_server)
        # Also copy it to the PRTP application directory as backup
        sensor_list_path = (self._log_base / "sensor.list").resolve()
        self._create_sensor_list(sensor_list_path, num_sensors)
        
        # Also create sensor.list in PRTP application dir for compatibility
        prtp_sensor_list = self.prtp_path / "sensor.list"
        self._create_sensor_list(prtp_sensor_list, num_sensors)
        _LOG.info("  Created sensor.list at: %s", sensor_list_path)
        _LOG.info("  Also copied to: %s", prtp_sensor_list)
        
        # Create clients config file (required by PRTP_server) with ABSOLUTE path
        client_config_path = (self._log_base / "clients.conf").resolve()
        self._create_client_config(client_config_path)
        
        # Find Q-table
        q_table_path = self._find_q_table()
        
        exe = self.prtp_path / "PRTP_server"
        cmd = [
            str(exe),
            f"-i{self.server_ip}",
            f"-p{self.sensor_port}",
            f"-s{self.client_port}",
            f"-l{sensor_list_path}",  # Absolute path
            f"-c{client_config_path}",  # Absolute path
        ]
        
        if q_table_path:
            cmd.append(f"-q{q_table_path}")
        
        _LOG.info("  Command: %s", ' '.join(cmd))
        
        try:
            if platform.system() == "Windows":
                self._server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self._server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid
                )
            
            self._processes.append(self._server_process)
            
            # Wait for server to initialize
            time.sleep(1.0)
            
            if self._server_process.poll() is not None:
                raise RuntimeError("PRTP_server exited immediately")
            
            _LOG.info("  PRTP_server started (PID: %d)", self._server_process.pid)
            
        except Exception as e:
            _LOG.error("Failed to start PRTP_server: %s", e)
            raise
    
    def start_clients(self, num: int) -> None:
        """
        Start PRTP clients.
        
        For PRTP, we need both:
        1. PRTP_client processes that subscribe to receive data
        2. Sensor simulators that send data to the server
        """
        _LOG.info("PRTP: Starting %d sensor/client pairs", num)
        
        # Determine sensor types - handle both list of strings and list of dicts
        sensor_config = self.cfg.get("sensors", ["temp", "humidity", "motion", "device"])
        sensor_types = []
        for s in sensor_config:
            if isinstance(s, dict):
                # Handle {'id': 'temp_0', 'type': 'temperature'} format
                sensor_types.append(s.get("type", s.get("id", "temp")).split("_")[0])
            else:
                sensor_types.append(str(s))
        
        # Start sensor simulators (these send data TO the server)
        for i in range(num):
            sensor_type = sensor_types[i % len(sensor_types)] if sensor_types else "temp"
            sensor = SensorSimulator(
                sensor_id=str(i),
                sensor_type=sensor_type,
                server_ip=self.server_ip,
                server_port=self.sensor_port,
                rate_hz=0  # We control sending in active mode
            )
            self._sensors.append(sensor)
        
        # Start PRTP_client processes (these receive data FROM the server)
        if self.prtp_path and (self.prtp_path / "PRTP_client").exists():
            # Use C binary clients
            for i in range(min(num, 10)):  # Limit client processes to avoid overload
                client = PRTPClientWrapper(
                    client_id=i,
                    server_ip=self.server_ip,
                    server_port=self.client_port,
                    prtp_bin_path=self.prtp_path,
                    log_dir=self._log_base
                )
                try:
                    client.start(subscribe_all=True)
                    self._clients.append(client)
                    time.sleep(0.1)  # Stagger client connections
                except Exception as e:
                    _LOG.warning("Failed to start client %d: %s", i, e)
            
            # Wait for clients to subscribe
            time.sleep(1.0)
            _LOG.info("  Started %d PRTP_client processes", len(self._clients))
        else:
            _LOG.warning("PRTP_client not found, running in sensor-only mode")
        
        _LOG.info("  Started %d sensor simulators", len(self._sensors))
    
    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """
        Send sensor data to PRTP server.
        
        In PRTP architecture:
        - Sensors send data to server's sensor_port
        - Server distributes to subscribed clients
        
        We track send times by (sensor_id, seq_no) so we can match them
        with receive times from client logs for REAL latency calculation.
        """
        if not self._alive:
            return False, 0.0
        
        try:
            # Get sensor for this client
            idx = int(client_id.split("_")[-1]) if "_" in client_id else 0
            if idx >= len(self._sensors):
                idx = idx % max(len(self._sensors), 1)
            
            if not self._sensors:
                # Create sensor on-demand
                sensor = SensorSimulator(
                    sensor_id=str(idx),
                    sensor_type="temp",
                    server_ip=self.server_ip,
                    server_port=self.sensor_port,
                    rate_hz=0
                )
                self._sensors.append(sensor)
            else:
                sensor = self._sensors[idx]
            
            # Get the next seq_no BEFORE sending
            next_seq = sensor.seq_no + 1
            
            # Send data
            success, send_time = sensor.send_once(data)
            
            if success:
                self._msg_count += 1
                
                # Store send time keyed by (sensor_id, seq_no) for later latency calculation
                key = (sensor.sensor_id, next_seq)
                self._send_times[key] = send_time
                
                # Return perf_counter time - the orchestrator will use this
                # We'll compute REAL latency in stop() from client logs
                return True, time.perf_counter()
            
            return False, 0.0
            
        except Exception as e:
            _LOG.error("PRTP send error: %s", e)
            return False, 0.0
    
    def stop(self) -> None:
        """Stop all PRTP processes and collect metrics."""
        self._alive = False
        _LOG.info("Stopping PRTP protocol...")
        
        # Stop sensors first
        for sensor in self._sensors:
            sensor.stop()
        
        # Give time for last messages to be delivered
        time.sleep(1.0)
        
        # Stop clients and collect metrics
        all_receive_times = {}  # sensor_id -> [(timestamp, seq_no, data)]
        for client in self._clients:
            # Check if client is still running
            if client.process and client.process.poll() is None:
                _LOG.debug("Client %d is running (PID %d), stopping...", 
                          client.client_id, client.process.pid)
                client.stop()
                time.sleep(0.5)  # Extra time for log flush
            else:
                exit_code = client.process.poll() if client.process else 'N/A'
                _LOG.warning("Client %d already exited with code %s before stop() called!",
                           client.client_id, exit_code)
            
            metrics = client.collect_metrics()
            self._recv_count += metrics.get("messages_received", 0)
            
            # Merge receive times from this client
            for sensor_id, entries in metrics.get("receive_times", {}).items():
                if sensor_id not in all_receive_times:
                    all_receive_times[sensor_id] = []
                all_receive_times[sensor_id].extend(entries)
        
        # Calculate REAL end-to-end latencies by matching send times with receive times
        _LOG.info("Calculating REAL end-to-end latencies...")
        self._calculate_real_latencies(all_receive_times)
        
        # Stop server
        if self._server_process and self._server_process.poll() is None:
            try:
                if platform.system() == "Windows":
                    self._server_process.terminate()
                else:
                    os.killpg(os.getpgid(self._server_process.pid), signal.SIGINT)
                    time.sleep(0.5)
                    if self._server_process.poll() is None:
                        os.killpg(os.getpgid(self._server_process.pid), signal.SIGKILL)
            except Exception as e:
                _LOG.warning("Error stopping server: %s", e)
        
        # Stop Python stub server if used
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass
        
        # Stop any remaining processes
        for proc in self._processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except:
                    pass
        
        _LOG.info("PRTP stopped. Sent: %d, Received: %d, Latency samples: %d", 
                  self._msg_count, self._recv_count, len(self._lat))
    
    def _calculate_real_latencies(self, receive_times: Dict[str, List[Tuple[float, int, str]]]) -> None:
        """
        Calculate REAL end-to-end latencies by matching send times with receive times.
        
        We stored send times as: self._send_times[(sensor_id, seq_no)] = send_time (Unix timestamp)
        Client logs give us:     receive_times[sensor_id] = [(recv_timestamp, seq_no, data), ...]
        
        Latency = recv_timestamp - send_time
        
        Two matching strategies are used:
        1. Exact match by (sensor_id, seq_no) key
        2. Fallback: Order-based matching per sensor_id (when seq_no=0 in logs)
        """
        matched = 0
        matched_keys = set()  # Track which (sensor_id, seq_no) pairs we've already matched
        
        # Strategy 1: Exact (sensor_id, seq_no) matching
        for sensor_id, entries in receive_times.items():
            # Sort entries by timestamp to get first receive for each seq_no
            sorted_entries = sorted(entries, key=lambda x: x[0])
            
            for recv_ts, seq_no, data in sorted_entries:
                key = (sensor_id, seq_no)
                
                # Skip if we've already matched this (sensor_id, seq_no)
                if key in matched_keys:
                    continue
                
                if key in self._send_times:
                    send_ts = self._send_times[key]
                    latency_ms = (recv_ts - send_ts) * 1000.0  # Convert to ms
                    
                    if -50 < latency_ms < 10000:
                        actual_latency = abs(latency_ms) if latency_ms < 0 else latency_ms
                        
                        # Apply RTT mode: double for round-trip approximation
                        if self.latency_mode in ("rtt", "rtt_approx"):
                            actual_latency *= 2.0  # Approximate RTT = 2 * one-way
                        
                        self._lat.append(actual_latency)
                        matched += 1
                        matched_keys.add(key)
        
        _LOG.info("  Strategy 1 (exact key match): %d pairs matched", matched)
        
        # Strategy 2: Order-based matching (fallback for when seq_no is not preserved)
        # Only use this if Strategy 1 didn't find any matches
        if matched == 0 and len(self._send_times) > 0:
            _LOG.info("  Trying Strategy 2: Order-based matching by sensor_id...")
            
            # Group send times by sensor_id
            send_by_sensor: Dict[str, List[Tuple[int, float]]] = {}  # sensor_id -> [(seq_no, send_time)]
            for (sensor_id, seq_no), send_time in self._send_times.items():
                if sensor_id not in send_by_sensor:
                    send_by_sensor[sensor_id] = []
                send_by_sensor[sensor_id].append((seq_no, send_time))
            
            # Sort send times by timestamp for each sensor
            for sensor_id in send_by_sensor:
                send_by_sensor[sensor_id].sort(key=lambda x: x[1])  # Sort by send_time
            
            for sensor_id, entries in receive_times.items():
                if sensor_id not in send_by_sensor:
                    continue
                
                # Sort receive entries by timestamp
                sorted_recv = sorted(entries, key=lambda x: x[0])
                send_list = send_by_sensor[sensor_id]
                
                # Match by order - take min of send and receive counts
                num_to_match = min(len(send_list), len(sorted_recv))
                
                for i in range(num_to_match):
                    _, send_ts = send_list[i]
                    recv_ts, _, _ = sorted_recv[i]
                    
                    latency_ms = (recv_ts - send_ts) * 1000.0
                    
                    # Accept reasonable latencies
                    if 0 <= latency_ms < 5000:  # 0 to 5 seconds
                        # Apply RTT mode: double for round-trip approximation
                        if self.latency_mode in ("rtt", "rtt_approx"):
                            latency_ms *= 2.0
                        self._lat.append(latency_ms)
                        matched += 1
                    elif -100 < latency_ms < 0:
                        # Small negative - clock skew, use absolute
                        abs_lat = abs(latency_ms)
                        if self.latency_mode in ("rtt", "rtt_approx"):
                            abs_lat *= 2.0
                        self._lat.append(abs_lat)
                        matched += 1
            
            _LOG.info("  Strategy 2 (order-based): %d additional pairs matched", matched)
        
        _LOG.info("  Total latency samples: %d", len(self._lat))
        
        if matched == 0 and len(self._send_times) > 0:
            _LOG.warning("  Could not match any send/receive pairs!")
            _LOG.warning("  Send times keys (sample): %s", list(self._send_times.keys())[:5])
            _LOG.warning("  Receive times keys (sample): %s", list(receive_times.keys())[:5])
    
    def is_alive(self) -> bool:
        return self._alive
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return PRTP metrics."""
        return {
            "protocol": "prtp",
            "mode": self.mode,
            "messages_sent": self._msg_count,
            "messages_received": self._recv_count,
            "latencies": self._lat.copy() if self._lat else [],
            "num_sensors": len(self._sensors),
            "num_clients": len(self._clients),
        }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect and return comprehensive metrics including latency statistics.
        This is called after stop() to get final results.
        """
        # Determine latency measurement description
        lat_mode_desc = "RTT (2x one-way)" if self.latency_mode in ("rtt", "rtt_approx") else "one-way"
        
        metrics = {
            "protocol": "prtp",
            "mode": self.mode,
            "latency_mode": self.latency_mode,
            "latency_mode_description": lat_mode_desc,
            "messages_sent": self._msg_count,
            "messages_received": self._recv_count,
            "packet_loss_pct": 0.0,
            "real_latencies_ms": self._lat.copy() if self._lat else [],
            "average_latency_ms": None,
            "min_latency_ms": None,
            "max_latency_ms": None,
            "std_latency_ms": None,
            "num_sensors": len(self._sensors),
            "num_clients": len(self._clients),
        }
        
        # Calculate packet loss
        if self._msg_count > 0:
            metrics["packet_loss_pct"] = ((self._msg_count - self._recv_count) / self._msg_count) * 100
        
        # Calculate latency statistics
        if self._lat:
            import statistics
            metrics["average_latency_ms"] = statistics.mean(self._lat)
            metrics["min_latency_ms"] = min(self._lat)
            metrics["max_latency_ms"] = max(self._lat)
            if len(self._lat) > 1:
                metrics["std_latency_ms"] = statistics.stdev(self._lat)
            else:
                metrics["std_latency_ms"] = 0.0
        
        return metrics
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _create_sensor_list(self, path: Path, num_sensors: int = None) -> None:
        """
        Create sensor.list file required by PRTP_server.
        
        Args:
            path: Path to write sensor.list file
            num_sensors: Number of sensors to create. If None, uses config.
        """
        sensor_config = self.cfg.get("sensors", ["temp", "humidity", "motion", "device"])
        
        # Handle both list of strings and list of dicts
        sensor_types = []
        for s in sensor_config:
            if isinstance(s, dict):
                sensor_types.append(s.get("type", s.get("id", "temp")).split("_")[0])
            else:
                sensor_types.append(str(s))
        
        # Use provided num_sensors or fall back to config
        if num_sensors is None:
            num_sensors = self.cfg.get("num_clients", 4)
        
        # Save the number for later use
        self._num_sensors = num_sensors
        
        with open(path, 'w') as f:
            for i in range(num_sensors):
                sensor_type = sensor_types[i % len(sensor_types)] if sensor_types else "temp"
                f.write(f"{sensor_type}_{i}\n")
        
        _LOG.debug("Created sensor.list with %d sensors: %s", num_sensors, path)
    
    def _create_client_config(self, path: Path) -> None:
        """
        Create clients config file required by PRTP_server.
        Format: #delay(ms)  p_prob  q_prob
        """
        with open(path, 'w') as f:
            f.write("#delay(ms)  p_prob  q_prob\n")
            f.write("0           0.0     1.0\n")
        
        _LOG.debug("Created clients.conf at %s", path)
    
    def _find_q_table(self) -> Optional[str]:
        """Find Q-learning table file."""
        candidates = [
            self.prtp_path / "q_agent_trained.csv" if self.prtp_path else None,
            self.launcher_path / "q_agent_trained.csv" if self.launcher_path else None,
            Path("./q_agent_trained.csv"),
        ]
        
        for path in candidates:
            if path and path.exists():
                return str(path)
        
        return None
    
    def _start_python_server_stub(self) -> None:
        """
        Start a Python-based server stub when C binary is not available.
        This is for development/testing only.
        """
        _LOG.warning("Using Python server stub (for development only)")
        
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.server_ip, self.sensor_port))
        self._server_socket.settimeout(1.0)
        
        def server_loop():
            while self._alive:
                try:
                    data, addr = self._server_socket.recvfrom(4096)
                    self._recv_count += 1
                    _LOG.debug("Stub server received %d bytes from %s", len(data), addr)
                except socket.timeout:
                    continue
                except OSError:
                    break
        
        self._server_thread = threading.Thread(target=server_loop, daemon=True)
        self._server_thread.start()
