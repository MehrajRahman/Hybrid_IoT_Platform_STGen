#!/usr/bin/env python3
"""
DCOSS Paper Benchmark: MQTT vs CoAP vs PRTP Protocol Comparison

This script runs comprehensive benchmarks comparing three IoT protocols:
- MQTT: Industry-standard pub/sub protocol (TCP-based)
- CoAP: Constrained Application Protocol (UDP-based, REST-like)
- PRTP: Publish/Subscribe Real-Time Protocol (UDP-based, Q-learning CC)

Experiments designed for DCOSS (IEEE International Conference on Distributed 
Computing in Smart Systems) paper submission.

Key Metrics:
- Latency (avg, p50, p95, p99)
- Throughput (messages/sec)
- Packet Loss Rate
- Network Tax (overhead bytes)
- Scalability (10, 50, 100, 500, 1000 nodes)

Usage:
    python run_dcoss_benchmark.py --quick          # Quick 5-minute test
    python run_dcoss_benchmark.py --full           # Complete benchmark suite
    python run_dcoss_benchmark.py --scalability    # Scalability tests only
    python run_dcoss_benchmark.py --network-tax    # Network overhead analysis
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import statistics
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import shutil

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not installed. Resource monitoring disabled. Install with: pip install psutil")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
_LOG = logging.getLogger("dcoss_benchmark")

# ============================================================================
# Configuration
# ============================================================================

# Protocols to compare
PROTOCOLS = ["mqtt", "coap", "prtp"]

# Scalability test node counts
SCALABILITY_NODES = [10, 50, 100, 500, 1000]

# Network conditions to test
NETWORK_CONDITIONS = {
    "ideal": {"loss": 0.0, "delay": 0, "jitter": 0},
    "wifi": {"loss": 1.0, "delay": 20, "jitter": 10},
    "cellular_3g": {"loss": 2.0, "delay": 100, "jitter": 50},
    "congested": {"loss": 5.0, "delay": 50, "jitter": 25},
    "lossy": {"loss": 10.0, "delay": 30, "jitter": 15},
}

# Test durations (seconds)
QUICK_DURATION = 15
STANDARD_DURATION = 60
EXTENDED_DURATION = 300

# Statistical configuration
DEFAULT_ITERATIONS = 5      # Number of runs for statistical significance
QUICK_ITERATIONS = 3        # Fewer iterations for quick tests
WARMUP_DURATION = 5         # Seconds to discard at start (Q-learning convergence)
COOLDOWN_BETWEEN_RUNS = 3   # Seconds between iterations


# ============================================================================
# Resource Monitoring
# ============================================================================

class ResourceMonitor:
    """
    Background thread that samples CPU and memory usage during tests.
    Essential for DCOSS paper to show protocol overhead.
    """
    
    def __init__(self, sample_interval: float = 0.5):
        self.sample_interval = sample_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._samples: List[Dict[str, float]] = []
        self._process: Optional["psutil.Process"] = None
    
    def start(self, pid: int = None):
        """Start monitoring. If pid provided, monitor that process; else system-wide."""
        if not PSUTIL_AVAILABLE:
            return
        
        self._samples = []
        self._running = True
        
        if pid:
            try:
                self._process = psutil.Process(pid)
            except psutil.NoSuchProcess:
                self._process = None
        else:
            self._process = None
        
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> Dict[str, float]:
        """Stop monitoring and return aggregated statistics."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        
        return self._compute_stats()
    
    def _sample_loop(self):
        """Background sampling loop."""
        while self._running:
            try:
                sample = {"timestamp": time.time()}
                
                if self._process:
                    # Process-specific monitoring
                    sample["cpu_percent"] = self._process.cpu_percent()
                    mem_info = self._process.memory_info()
                    sample["memory_mb"] = mem_info.rss / (1024 * 1024)
                else:
                    # System-wide monitoring
                    sample["cpu_percent"] = psutil.cpu_percent(interval=None)
                    mem = psutil.virtual_memory()
                    sample["memory_mb"] = mem.used / (1024 * 1024)
                    sample["memory_percent"] = mem.percent
                
                self._samples.append(sample)
                
            except Exception:
                pass  # Process may have exited
            
            time.sleep(self.sample_interval)
    
    def _compute_stats(self) -> Dict[str, float]:
        """Compute CPU/memory statistics from samples."""
        if not self._samples:
            return {"cpu_avg": 0, "cpu_max": 0, "memory_avg_mb": 0, "memory_max_mb": 0}
        
        cpu_values = [s["cpu_percent"] for s in self._samples if "cpu_percent" in s]
        mem_values = [s["memory_mb"] for s in self._samples if "memory_mb" in s]
        
        return {
            "cpu_avg": statistics.mean(cpu_values) if cpu_values else 0,
            "cpu_max": max(cpu_values) if cpu_values else 0,
            "cpu_std": statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0,
            "memory_avg_mb": statistics.mean(mem_values) if mem_values else 0,
            "memory_max_mb": max(mem_values) if mem_values else 0,
            "num_samples": len(self._samples)
        }


def compute_statistics(values: List[float]) -> Dict[str, float]:
    """
    Compute mean, std dev, and confidence interval for a list of values.
    Returns dict with mean, std, ci_95 (95% confidence interval half-width).
    """
    if not values:
        return {"mean": 0, "std": 0, "ci_95": 0, "min": 0, "max": 0}
    
    n = len(values)
    mean = statistics.mean(values)
    
    if n > 1:
        std = statistics.stdev(values)
        # 95% CI using t-distribution approximation (t ≈ 2.0 for n=5)
        t_value = 2.776 if n <= 5 else 2.262 if n <= 10 else 1.96
        ci_95 = t_value * std / (n ** 0.5)
    else:
        std = 0
        ci_95 = 0
    
    return {
        "mean": mean,
        "std": std,
        "ci_95": ci_95,
        "min": min(values),
        "max": max(values),
        "n": n
    }


# ============================================================================
# Benchmark Classes
# ============================================================================

class DCOSSBenchmark:
    """Main benchmark runner for DCOSS paper experiments."""
    
    def __init__(self, output_dir: str = None, iterations: int = DEFAULT_ITERATIONS,
                 warmup_duration: int = WARMUP_DURATION, monitor_resources: bool = True):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir or f"results/dcoss_benchmark_{self.timestamp}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistical configuration
        self.iterations = iterations
        self.warmup_duration = warmup_duration
        self.monitor_resources = monitor_resources and PSUTIL_AVAILABLE
        
        self.results: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "protocols": PROTOCOLS,
            "config": {
                "iterations": iterations,
                "warmup_duration": warmup_duration,
                "resource_monitoring": self.monitor_resources
            },
            "experiments": {},
        }
        
        _LOG.info(f"DCOSS Benchmark initialized. Results: {self.output_dir}")
        _LOG.info(f"  Iterations per test: {iterations}, Warmup: {warmup_duration}s")
        if self.monitor_resources:
            _LOG.info(f"  Resource monitoring: ENABLED (psutil)")
        else:
            _LOG.info(f"  Resource monitoring: DISABLED")
    
    def run_latency_comparison(self, num_clients: int = 100, duration: int = 30) -> Dict:
        """
        Experiment 1: Latency Comparison
        
        Measures end-to-end latency for each protocol under identical conditions.
        Runs multiple iterations for statistical significance.
        """
        _LOG.info("=" * 70)
        _LOG.info("EXPERIMENT 1: Latency Comparison")
        _LOG.info(f"  Clients: {num_clients}, Duration: {duration}s, Iterations: {self.iterations}")
        _LOG.info(f"  Warmup: {self.warmup_duration}s (metrics discarded)")
        _LOG.info("=" * 70)
        
        results = {}
        
        for protocol in PROTOCOLS:
            _LOG.info(f"\n>>> Testing {protocol.upper()} ({self.iterations} iterations) <<<")
            
            # Collect results from multiple runs
            run_results = []
            resource_stats_list = []
            
            for iteration in range(self.iterations):
                _LOG.info(f"    Run {iteration + 1}/{self.iterations}...")
                
                # Start resource monitoring
                resource_monitor = ResourceMonitor() if self.monitor_resources else None
                if resource_monitor:
                    resource_monitor.start()
                
                result = self._run_single_test(
                    protocol=protocol,
                    num_clients=num_clients,
                    duration=duration + self.warmup_duration,  # Extra time for warmup
                    scenario_name="latency_test"
                )
                
                # Stop resource monitoring
                if resource_monitor:
                    resource_stats = resource_monitor.stop()
                    resource_stats_list.append(resource_stats)
                
                if "error" not in result:
                    run_results.append(result)
                else:
                    _LOG.warning(f"    Run {iteration + 1} failed: {result.get('error')}")
                
                # Cool-down between iterations
                if iteration < self.iterations - 1:
                    time.sleep(COOLDOWN_BETWEEN_RUNS)
            
            # Aggregate results with statistics
            results[protocol] = self._aggregate_runs(run_results, resource_stats_list)
            
            # Cool-down between protocols
            time.sleep(3)
        
        self.results["experiments"]["latency_comparison"] = {
            "config": {
                "num_clients": num_clients, 
                "duration": duration,
                "iterations": self.iterations,
                "warmup_duration": self.warmup_duration
            },
            "results": results
        }
        
        self._print_latency_summary(results)
        return results
    
    def run_throughput_comparison(self, num_clients: int = 100, duration: int = 30) -> Dict:
        """
        Experiment 2: Throughput Comparison
        
        Measures maximum sustainable message rate for each protocol.
        Runs multiple iterations for statistical significance.
        """
        _LOG.info("=" * 70)
        _LOG.info("EXPERIMENT 2: Throughput Comparison")
        _LOG.info(f"  Clients: {num_clients}, Duration: {duration}s, Iterations: {self.iterations}")
        _LOG.info("=" * 70)
        
        results = {}
        
        for protocol in PROTOCOLS:
            _LOG.info(f"\n>>> Testing {protocol.upper()} ({self.iterations} iterations) <<<")
            
            run_results = []
            resource_stats_list = []
            
            for iteration in range(self.iterations):
                _LOG.info(f"    Run {iteration + 1}/{self.iterations}...")
                
                resource_monitor = ResourceMonitor() if self.monitor_resources else None
                if resource_monitor:
                    resource_monitor.start()
                
                result = self._run_single_test(
                    protocol=protocol,
                    num_clients=num_clients,
                    duration=duration + self.warmup_duration,
                    scenario_name="throughput_test",
                    high_rate=True
                )
                
                if resource_monitor:
                    resource_stats = resource_monitor.stop()
                    resource_stats_list.append(resource_stats)
                
                if "error" not in result:
                    run_results.append(result)
                else:
                    _LOG.warning(f"    Run {iteration + 1} failed: {result.get('error')}")
                
                if iteration < self.iterations - 1:
                    time.sleep(COOLDOWN_BETWEEN_RUNS)
            
            results[protocol] = self._aggregate_runs(run_results, resource_stats_list)
            time.sleep(3)
        
        self.results["experiments"]["throughput_comparison"] = {
            "config": {
                "num_clients": num_clients, 
                "duration": duration,
                "iterations": self.iterations
            },
            "results": results
        }
        
        self._print_throughput_summary(results)
        return results
        return results
    
    def run_scalability_test(self, node_counts: List[int] = None, duration: int = 30) -> Dict:
        """
        Experiment 3: Scalability Test
        
        Tests protocol performance as number of nodes increases.
        """
        node_counts = node_counts or SCALABILITY_NODES
        
        _LOG.info("=" * 70)
        _LOG.info("EXPERIMENT 3: Scalability Test")
        _LOG.info(f"  Node counts: {node_counts}")
        _LOG.info("=" * 70)
        
        results = {proto: {} for proto in PROTOCOLS}
        
        for num_clients in node_counts:
            _LOG.info(f"\n--- Testing with {num_clients} nodes ---")
            
            for protocol in PROTOCOLS:
                _LOG.info(f"  {protocol.upper()}: {num_clients} clients...")
                
                result = self._run_single_test(
                    protocol=protocol,
                    num_clients=num_clients,
                    duration=duration,
                    scenario_name=f"scale_{num_clients}"
                )
                
                results[protocol][num_clients] = result
                time.sleep(2)
        
        self.results["experiments"]["scalability"] = {
            "config": {"node_counts": node_counts, "duration": duration},
            "results": results
        }
        
        self._print_scalability_summary(results, node_counts)
        return results
    
    def run_network_conditions_test(self, num_clients: int = 50, duration: int = 30) -> Dict:
        """
        Experiment 4: Network Conditions Impact
        
        Tests protocol robustness under various network impairments.
        """
        _LOG.info("=" * 70)
        _LOG.info("EXPERIMENT 4: Network Conditions Impact")
        _LOG.info(f"  Clients: {num_clients}")
        _LOG.info("=" * 70)
        
        # Check if we can apply network impairments
        _LOG.info("  Checking network impairment capability...")
        test_apply = self._apply_network_impairment(loss=1.0, delay=10, jitter=5)
        self._remove_network_impairment()
        if not test_apply:
            _LOG.warning("=" * 70)
            _LOG.warning("WARNING: Network impairment requires sudo!")
            _LOG.warning("  Run with: sudo -E $(which python) run_dcoss_benchmark.py ...")
            _LOG.warning("  OR configure passwordless sudo for 'tc' command")
            _LOG.warning("  Results will show BASELINE performance (no impairment)")
            _LOG.warning("=" * 70)
        
        results = {proto: {} for proto in PROTOCOLS}
        
        for condition_name, params in NETWORK_CONDITIONS.items():
            _LOG.info(f"\n--- Condition: {condition_name} ---")
            _LOG.info(f"    Loss: {params['loss']}%, Delay: {params['delay']}ms, Jitter: {params['jitter']}ms")
            
            # Apply network impairment
            impairment_applied = self._apply_network_impairment(
                params['loss'], params['delay'], params['jitter']
            )
            
            try:
                for protocol in PROTOCOLS:
                    _LOG.info(f"  Testing {protocol.upper()}...")
                    
                    result = self._run_single_test(
                        protocol=protocol,
                        num_clients=num_clients,
                        duration=duration,
                        scenario_name=f"network_{condition_name}"
                    )
                    
                    # Mark if impairment was actually applied
                    result["impairment_applied"] = impairment_applied
                    results[protocol][condition_name] = result
                    time.sleep(2)
            finally:
                # Always cleanup
                self._remove_network_impairment()
        
        self.results["experiments"]["network_conditions"] = {
            "config": {
                "num_clients": num_clients, 
                "duration": duration,
                "conditions": NETWORK_CONDITIONS
            },
            "results": results
        }
        
        self._print_network_summary(results)
        return results
    
    def run_reliability_test(self, num_clients: int = 50, duration: int = 30) -> Dict:
        """
        Experiment 5: Reliability Comparison
        
        Tests packet loss and delivery guarantees for each protocol.
        """
        _LOG.info("=" * 70)
        _LOG.info("EXPERIMENT 5: Reliability Comparison")
        _LOG.info("=" * 70)
        
        results = {}
        
        # Test with different reliability settings
        reliability_configs = {
            "mqtt_qos0": {"protocol": "mqtt", "qos": 0},
            "mqtt_qos1": {"protocol": "mqtt", "qos": 1},
            "mqtt_qos2": {"protocol": "mqtt", "qos": 2},
            "coap_non": {"protocol": "coap", "confirmable": False},
            "coap_con": {"protocol": "coap", "confirmable": True},
            "prtp_unreliable": {"protocol": "prtp", "reliable": False},
            "prtp_reliable": {"protocol": "prtp", "reliable": True},
        }
        
        # Apply moderate network impairment for meaningful results
        self._apply_network_impairment(loss=2.0, delay=20, jitter=10)
        
        try:
            for config_name, config in reliability_configs.items():
                _LOG.info(f"\n  Testing {config_name}...")
                
                result = self._run_single_test(
                    protocol=config["protocol"],
                    num_clients=num_clients,
                    duration=duration,
                    scenario_name=f"reliability_{config_name}",
                    extra_config=config
                )
                
                results[config_name] = result
                time.sleep(2)
        finally:
            self._remove_network_impairment()
        
        self.results["experiments"]["reliability"] = {
            "config": {"num_clients": num_clients, "duration": duration},
            "results": results
        }
        
        self._print_reliability_summary(results)
        return results
    
    def run_full_benchmark(self) -> Dict:
        """Run complete benchmark suite for DCOSS paper."""
        _LOG.info("=" * 70)
        _LOG.info("DCOSS FULL BENCHMARK SUITE")
        _LOG.info("=" * 70)
        
        start_time = time.time()
        
        # Run all experiments
        self.run_latency_comparison(num_clients=100, duration=STANDARD_DURATION)
        self.run_throughput_comparison(num_clients=100, duration=STANDARD_DURATION)
        self.run_scalability_test(duration=30)
        self.run_network_conditions_test(num_clients=50, duration=30)
        self.run_reliability_test(num_clients=50, duration=30)
        
        elapsed = time.time() - start_time
        self.results["total_duration_seconds"] = elapsed
        
        _LOG.info(f"\nFull benchmark completed in {elapsed/60:.1f} minutes")
        
        # Generate reports
        self.generate_report()
        self.generate_latex_tables()
        
        return self.results
    
    def run_quick_benchmark(self) -> Dict:
        """Run quick benchmark for testing."""
        _LOG.info("=" * 70)
        _LOG.info("DCOSS QUICK BENCHMARK")
        _LOG.info("=" * 70)
        
        self.run_latency_comparison(num_clients=20, duration=QUICK_DURATION)
        self.run_throughput_comparison(num_clients=20, duration=QUICK_DURATION)
        
        self.generate_report()
        self.generate_latex_tables()
        return self.results
    
    # =========================================================================
    # Internal Methods
    # =========================================================================
    
    def _aggregate_runs(self, run_results: List[Dict], resource_stats_list: List[Dict] = None) -> Dict:
        """
        Aggregate results from multiple runs into mean ± std statistics.
        This is critical for DCOSS paper to show statistical significance.
        """
        if not run_results:
            return {"error": "All runs failed", "n_runs": 0}
        
        # Extract values for each metric across runs
        metrics = {
            "lat_avg_ms": [],
            "lat_p50_ms": [],
            "lat_p95_ms": [],
            "lat_p99_ms": [],
            "lat_min_ms": [],
            "lat_max_ms": [],
            "sent": [],
            "recv": [],
            "loss": [],
        }
        
        for result in run_results:
            for metric in metrics:
                if metric in result:
                    metrics[metric].append(result[metric])
        
        # Compute statistics for each metric
        aggregated = {
            "n_runs": len(run_results),
            "protocol": run_results[0].get("protocol", "unknown"),
        }
        
        for metric, values in metrics.items():
            if values:
                stats = compute_statistics(values)
                aggregated[metric] = stats["mean"]
                aggregated[f"{metric}_std"] = stats["std"]
                aggregated[f"{metric}_ci95"] = stats["ci_95"]
        
        # Aggregate resource statistics if available
        if resource_stats_list:
            cpu_avgs = [s.get("cpu_avg", 0) for s in resource_stats_list]
            mem_avgs = [s.get("memory_avg_mb", 0) for s in resource_stats_list]
            cpu_maxs = [s.get("cpu_max", 0) for s in resource_stats_list]
            mem_maxs = [s.get("memory_max_mb", 0) for s in resource_stats_list]
            
            if cpu_avgs:
                cpu_stats = compute_statistics(cpu_avgs)
                aggregated["cpu_avg"] = cpu_stats["mean"]
                aggregated["cpu_avg_std"] = cpu_stats["std"]
                aggregated["cpu_max"] = max(cpu_maxs) if cpu_maxs else 0
            
            if mem_avgs:
                mem_stats = compute_statistics(mem_avgs)
                aggregated["memory_avg_mb"] = mem_stats["mean"]
                aggregated["memory_avg_mb_std"] = mem_stats["std"]
                aggregated["memory_max_mb"] = max(mem_maxs) if mem_maxs else 0
        
        return aggregated
    
    def _run_single_test(self, protocol: str, num_clients: int, duration: int,
                         scenario_name: str, high_rate: bool = False,
                         extra_config: Dict = None) -> Dict:
        """Run a single protocol test and collect metrics."""
        
        # Create temporary config
        config = {
            "protocol": protocol,
            "mode": "active",
            "server_ip": "127.0.0.1",
            "num_clients": num_clients,
            "duration": duration,
            "sensors": ["temp"],
            "traffic_pattern": {
                "temp": {"rate_hz": 50 if high_rate else 10, "burst": False}
            }
        }
        
        # Protocol-specific defaults
        if protocol == "mqtt":
            config["server_port"] = 1883
            config["topic"] = "stgen/sensors"
            config["qos"] = extra_config.get("qos", 1) if extra_config else 1
        elif protocol == "coap":
            config["server_port"] = 5683
        elif protocol == "prtp":
            config["server_port"] = 5001
            config["sensor_port"] = 5000
            config["reliable"] = extra_config.get("reliable", False) if extra_config else False
            config["q_learning_enabled"] = True
            # RTT mode for fair comparison with MQTT/CoAP (they measure full round-trip)
            config["latency_mode"] = extra_config.get("latency_mode", "rtt_approx") if extra_config else "rtt_approx"
        
        # Apply extra config
        if extra_config:
            config.update(extra_config)
        
        # Write temp config
        config_file = Path(f"temp_{protocol}_config.json")
        config_file.write_text(json.dumps(config, indent=2))
        
        try:
            # Run STGen
            result = subprocess.run(
                [sys.executable, "-m", "stgen.main", str(config_file)],
                capture_output=True,
                text=True,
                timeout=duration + 180  # Extra time for setup/teardown
            )
            
            if result.returncode != 0:
                _LOG.warning(f"{protocol} test returned non-zero: {result.stderr[:200]}")
            
            # Load results - FIXED: sort by modification time, not alphabetically
            # This ensures we get the NEWEST result, not the one with the highest name
            result_dirs = list(Path("results").glob(f"{protocol}_*"))
            if result_dirs:
                # Sort by modification time (newest last)
                latest = max(result_dirs, key=lambda d: d.stat().st_mtime)
                summary_file = latest / "summary.json"
                if summary_file.exists():
                    return json.loads(summary_file.read_text())
            
            return {"error": "No results found", "stderr": result.stderr[:500]}
            
        except subprocess.TimeoutExpired:
            return {"error": "Test timed out"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            config_file.unlink(missing_ok=True)
    
    def _apply_network_impairment(self, loss: float, delay: int, jitter: int) -> bool:
        """Apply network impairment using tc.
        
        Returns True if impairment was applied successfully.
        """
        if not shutil.which("tc"):
            _LOG.warning("tc not found, skipping network impairment")
            return False
        
        try:
            # Clean up first
            subprocess.run(
                ["sudo", "-n", "tc", "qdisc", "del", "dev", "lo", "root"],
                stderr=subprocess.DEVNULL, 
                stdout=subprocess.DEVNULL,
                check=False,
                timeout=5
            )
            
            if loss > 0 or delay > 0:
                result = subprocess.run([
                    "sudo", "-n", "tc", "qdisc", "add", "dev", "lo", "root", "netem",
                    "delay", f"{delay}ms", f"{jitter}ms",
                    "loss", f"{loss}%"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode != 0:
                    _LOG.error(f"Failed to apply network impairment: {result.stderr}")
                    _LOG.error("Run with: sudo -E python ... OR configure passwordless sudo for 'tc'")
                    return False
                
                # Verify it was applied
                verify = subprocess.run(["tc", "qdisc", "show", "dev", "lo"], 
                                       capture_output=True, text=True, timeout=5)
                if "netem" in verify.stdout:
                    _LOG.info(f"    ✓ Network impairment APPLIED: {delay}ms delay, {loss}% loss")
                    return True
                else:
                    _LOG.warning("    ✗ Network impairment NOT applied (tc didn't show netem)")
                    return False
            else:
                _LOG.info("    ✓ Clean network (no impairment)")
                return True
                
        except subprocess.TimeoutExpired:
            _LOG.warning("Network impairment command timed out")
            return False
        except subprocess.CalledProcessError as e:
            _LOG.error(f"Failed to apply network impairment: {e}")
            return False
        except Exception as e:
            _LOG.warning(f"Network impairment error: {e}")
            return False
    
    def _remove_network_impairment(self):
        """Remove network impairment."""
        if shutil.which("tc"):
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", "lo", "root"],
                stderr=subprocess.DEVNULL, check=False
            )
    
    # =========================================================================
    # Reporting (with statistical confidence intervals)
    # =========================================================================
    
    def _format_with_std(self, mean: float, std: float, precision: int = 2) -> str:
        """Format value as 'mean ± std' for display."""
        if std > 0:
            return f"{mean:.{precision}f}±{std:.{precision}f}"
        return f"{mean:.{precision}f}"
    
    def _print_latency_summary(self, results: Dict):
        """Print latency comparison table with confidence intervals."""
        print("\n" + "=" * 90)
        print("LATENCY COMPARISON RESULTS (mean ± std, n runs)")
        print("=" * 90)
        print(f"{'Protocol':<10} {'Runs':<6} {'Avg (ms)':<16} {'P50 (ms)':<16} {'P95 (ms)':<16} {'CPU %':<12}")
        print("-" * 90)
        
        for proto, data in results.items():
            if "error" in data:
                print(f"{proto.upper():<10} ERROR: {data['error']}")
            else:
                n_runs = data.get("n_runs", 1)
                avg = self._format_with_std(data.get("lat_avg_ms", 0), data.get("lat_avg_ms_std", 0))
                p50 = self._format_with_std(data.get("lat_p50_ms", 0), data.get("lat_p50_ms_std", 0))
                p95 = self._format_with_std(data.get("lat_p95_ms", 0), data.get("lat_p95_ms_std", 0))
                cpu = self._format_with_std(data.get("cpu_avg", 0), data.get("cpu_avg_std", 0), 1)
                print(f"{proto.upper():<10} {n_runs:<6} {avg:<16} {p50:<16} {p95:<16} {cpu:<12}")
        
        print("=" * 90)
    
    def _print_throughput_summary(self, results: Dict):
        """Print throughput comparison table with statistics."""
        print("\n" + "=" * 90)
        print("THROUGHPUT COMPARISON RESULTS (mean ± std)")
        print("=" * 90)
        print(f"{'Protocol':<10} {'Runs':<6} {'Sent':<12} {'Received':<12} {'Loss %':<14} {'Mem (MB)':<12}")
        print("-" * 90)
        
        for proto, data in results.items():
            if "error" in data:
                print(f"{proto.upper():<10} ERROR: {data['error']}")
            else:
                n_runs = data.get("n_runs", 1)
                sent = int(data.get("sent", 0))
                recv = int(data.get("recv", 0))
                loss = self._format_with_std(data.get("loss", 0) * 100, data.get("loss_std", 0) * 100, 2)
                mem = self._format_with_std(data.get("memory_avg_mb", 0), data.get("memory_avg_mb_std", 0), 1)
                print(f"{proto.upper():<10} {n_runs:<6} {sent:<12} {recv:<12} {loss:<14} {mem:<12}")
        
        print("=" * 90)
    
    def _print_scalability_summary(self, results: Dict, node_counts: List[int]):
        """Print scalability test summary."""
        print("\n" + "=" * 80)
        print("SCALABILITY TEST RESULTS")
        print("=" * 80)
        
        # Header
        header = f"{'Nodes':<10}"
        for proto in PROTOCOLS:
            header += f" {proto.upper():<20}"
        print(header)
        print("-" * 80)
        
        for num_clients in node_counts:
            row = f"{num_clients:<10}"
            for proto in PROTOCOLS:
                data = results[proto].get(num_clients, {})
                if "error" in data:
                    row += f" {'ERROR':<20}"
                else:
                    lat = data.get("lat_avg_ms", 0)
                    loss = data.get("loss", 0) * 100
                    row += f" {lat:.1f}ms/{loss:.1f}%loss   "
            print(row)
        
        print("=" * 80)
    
    def _print_network_summary(self, results: Dict):
        """Print network conditions test summary."""
        print("\n" + "=" * 80)
        print("NETWORK CONDITIONS TEST RESULTS")
        print("=" * 80)
        
        for condition in NETWORK_CONDITIONS.keys():
            print(f"\n--- {condition.upper()} ---")
            print(f"{'Protocol':<12} {'Latency (ms)':<15} {'Loss %':<10} {'Delivered':<12}")
            
            for proto in PROTOCOLS:
                data = results[proto].get(condition, {})
                if "error" in data:
                    print(f"{proto.upper():<12} ERROR")
                else:
                    lat = data.get("lat_avg_ms", 0)
                    loss = data.get("loss", 0) * 100
                    recv = data.get("recv", 0)
                    print(f"{proto.upper():<12} {lat:<15.2f} {loss:<10.2f} {recv:<12}")
        
        print("\n" + "=" * 80)
    
    def _print_reliability_summary(self, results: Dict):
        """Print reliability test summary."""
        print("\n" + "=" * 70)
        print("RELIABILITY TEST RESULTS")
        print("=" * 70)
        print(f"{'Config':<20} {'Sent':<10} {'Received':<10} {'Loss %':<10} {'Latency (ms)':<12}")
        print("-" * 70)
        
        for config_name, data in results.items():
            if "error" in data:
                print(f"{config_name:<20} ERROR")
            else:
                sent = data.get("sent", 0)
                recv = data.get("recv", 0)
                loss = data.get("loss", 0) * 100
                lat = data.get("lat_avg_ms", 0)
                print(f"{config_name:<20} {sent:<10} {recv:<10} {loss:<10.2f} {lat:<12.2f}")
        
        print("=" * 70)
    
    def generate_report(self):
        """Generate comprehensive benchmark report."""
        report_file = self.output_dir / "benchmark_report.json"
        report_file.write_text(json.dumps(self.results, indent=2))
        _LOG.info(f"Report saved to: {report_file}")
        
        # Text summary
        summary_file = self.output_dir / "summary.txt"
        with open(summary_file, 'w') as f:
            f.write("DCOSS BENCHMARK REPORT\n")
            f.write("=" * 70 + "\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Protocols: {', '.join(PROTOCOLS)}\n\n")
            
            for exp_name, exp_data in self.results.get("experiments", {}).items():
                f.write(f"\n{exp_name.upper()}\n")
                f.write("-" * 40 + "\n")
                f.write(json.dumps(exp_data.get("config", {}), indent=2) + "\n")
        
        _LOG.info(f"Summary saved to: {summary_file}")
    
    def generate_latex_tables(self):
        """Generate LaTeX tables for paper with confidence intervals."""
        latex_file = self.output_dir / "latex_tables.tex"
        
        def fmt_ci(mean: float, ci: float, precision: int = 2) -> str:
            """Format as mean ± CI for LaTeX."""
            if ci > 0:
                return f"${mean:.{precision}f} \\pm {ci:.{precision}f}$"
            return f"${mean:.{precision}f}$"
        
        with open(latex_file, 'w') as f:
            f.write("% Auto-generated LaTeX tables for DCOSS paper\n")
            f.write("% Generated: " + self.timestamp + "\n")
            f.write("% Statistical confidence: 95% CI from multiple runs\n\n")
            
            # Latency comparison table with CI
            if "latency_comparison" in self.results.get("experiments", {}):
                config = self.results["experiments"]["latency_comparison"]["config"]
                f.write("% Table: Latency Comparison (with 95% confidence intervals)\n")
                f.write("\\begin{table}[htbp]\n")
                f.write(f"\\caption{{End-to-End Latency Comparison (ms). {config.get('iterations', 1)} runs, {config.get('num_clients', 100)} clients.}}\n")
                f.write("\\label{tab:latency}\n")
                f.write("\\centering\n")
                f.write("\\begin{tabular}{lcccc}\n")
                f.write("\\hline\n")
                f.write("\\textbf{Protocol} & \\textbf{Avg Latency} & \\textbf{P50} & \\textbf{P95} & \\textbf{CPU \\%} \\\\\n")
                f.write("\\hline\n")
                
                data = self.results["experiments"]["latency_comparison"]["results"]
                for proto in PROTOCOLS:
                    if proto in data and "error" not in data[proto]:
                        d = data[proto]
                        avg = fmt_ci(d.get('lat_avg_ms', 0), d.get('lat_avg_ms_ci95', 0))
                        p50 = fmt_ci(d.get('lat_p50_ms', 0), d.get('lat_p50_ms_ci95', 0))
                        p95 = fmt_ci(d.get('lat_p95_ms', 0), d.get('lat_p95_ms_ci95', 0))
                        cpu = fmt_ci(d.get('cpu_avg', 0), d.get('cpu_avg_std', 0), 1)
                        f.write(f"{proto.upper()} & {avg} & {p50} & {p95} & {cpu} \\\\\n")
                
                f.write("\\hline\n")
                f.write("\\end{tabular}\n")
                f.write("\\end{table}\n\n")
            
            # Throughput comparison table
            if "throughput_comparison" in self.results.get("experiments", {}):
                config = self.results["experiments"]["throughput_comparison"]["config"]
                f.write("% Table: Throughput Comparison\n")
                f.write("\\begin{table}[htbp]\n")
                f.write(f"\\caption{{Throughput and Resource Usage. {config.get('iterations', 1)} runs.}}\n")
                f.write("\\label{tab:throughput}\n")
                f.write("\\centering\n")
                f.write("\\begin{tabular}{lcccc}\n")
                f.write("\\hline\n")
                f.write("\\textbf{Protocol} & \\textbf{Msg Delivered} & \\textbf{Loss \\%} & \\textbf{CPU \\%} & \\textbf{Mem (MB)} \\\\\n")
                f.write("\\hline\n")
                
                data = self.results["experiments"]["throughput_comparison"]["results"]
                for proto in PROTOCOLS:
                    if proto in data and "error" not in data[proto]:
                        d = data[proto]
                        recv = int(d.get('recv', 0))
                        loss = fmt_ci(d.get('loss', 0) * 100, d.get('loss_ci95', 0) * 100)
                        cpu = fmt_ci(d.get('cpu_avg', 0), d.get('cpu_avg_std', 0), 1)
                        mem = fmt_ci(d.get('memory_avg_mb', 0), d.get('memory_avg_mb_std', 0), 1)
                        f.write(f"{proto.upper()} & {recv} & {loss} & {cpu} & {mem} \\\\\n")
                
                f.write("\\hline\n")
                f.write("\\end{tabular}\n")
                f.write("\\end{table}\n\n")
            
            # Scalability table
            if "scalability" in self.results.get("experiments", {}):
                f.write("% Table: Scalability\n")
                f.write("\\begin{table}[htbp]\n")
                f.write("\\caption{Scalability: Average Latency (ms) vs Node Count}\n")
                f.write("\\label{tab:scalability}\n")
                f.write("\\centering\n")
                f.write("\\begin{tabular}{l" + "c" * len(PROTOCOLS) + "}\n")
                f.write("\\hline\n")
                f.write("\\textbf{Nodes} & " + " & ".join([f"\\textbf{{{p.upper()}}}" for p in PROTOCOLS]) + " \\\\\n")
                f.write("\\hline\n")
                
                data = self.results["experiments"]["scalability"]["results"]
                for nodes in self.results["experiments"]["scalability"]["config"]["node_counts"]:
                    row = [str(nodes)]
                    for proto in PROTOCOLS:
                        if str(nodes) in data.get(proto, {}) or nodes in data.get(proto, {}):
                            d = data[proto].get(nodes, data[proto].get(str(nodes), {}))
                            if "error" in d:
                                row.append("--")
                            else:
                                lat = d.get('lat_avg_ms', 0)
                                ci = d.get('lat_avg_ms_ci95', 0)
                                row.append(fmt_ci(lat, ci, 1))
                        else:
                            row.append("--")
                    f.write(" & ".join(row) + " \\\\\n")
                
                f.write("\\hline\n")
                f.write("\\end{tabular}\n")
                f.write("\\end{table}\n")
        
        _LOG.info(f"LaTeX tables saved to: {latex_file}")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="DCOSS Paper Benchmark: MQTT vs CoAP vs PRTP"
    )
    
    parser.add_argument("--quick", action="store_true",
                        help="Run quick benchmark (5 minutes)")
    parser.add_argument("--full", action="store_true",
                        help="Run full benchmark suite")
    parser.add_argument("--latency", action="store_true",
                        help="Run latency comparison only")
    parser.add_argument("--throughput", action="store_true",
                        help="Run throughput comparison only")
    parser.add_argument("--scalability", action="store_true",
                        help="Run scalability test only")
    parser.add_argument("--network", action="store_true",
                        help="Run network conditions test only")
    parser.add_argument("--reliability", action="store_true",
                        help="Run reliability test only")
    parser.add_argument("--nodes", type=int, default=100,
                        help="Number of nodes for single tests")
    parser.add_argument("--duration", type=int, default=30,
                        help="Test duration in seconds")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Number of iterations for statistical significance (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--warmup", type=int, default=WARMUP_DURATION,
                        help=f"Warmup period in seconds (metrics discarded, default: {WARMUP_DURATION})")
    parser.add_argument("--no-resource-monitor", action="store_true",
                        help="Disable CPU/Memory monitoring")
    parser.add_argument("--output", type=str,
                        help="Output directory")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("DCOSS BENCHMARK: MQTT vs CoAP vs PRTP")
    print("=" * 70)
    print(f"Protocols: {', '.join(PROTOCOLS)}")
    print(f"Iterations: {args.iterations}, Warmup: {args.warmup}s")
    print(f"Resource monitoring: {'DISABLED' if args.no_resource_monitor else 'ENABLED'}")
    print()
    
    benchmark = DCOSSBenchmark(
        output_dir=args.output,
        iterations=args.iterations,
        warmup_duration=args.warmup,
        monitor_resources=not args.no_resource_monitor
    )
    
    if args.quick:
        # Quick mode uses fewer iterations
        benchmark.iterations = QUICK_ITERATIONS
        benchmark.run_quick_benchmark()
    elif args.full:
        benchmark.run_full_benchmark()
    elif args.latency:
        benchmark.run_latency_comparison(args.nodes, args.duration)
        benchmark.generate_report()
        benchmark.generate_latex_tables()
    elif args.throughput:
        benchmark.run_throughput_comparison(args.nodes, args.duration)
        benchmark.generate_report()
        benchmark.generate_latex_tables()
    elif args.scalability:
        benchmark.run_scalability_test(duration=args.duration)
        benchmark.generate_report()
        benchmark.generate_latex_tables()
    elif args.network:
        benchmark.run_network_conditions_test(args.nodes, args.duration)
        benchmark.generate_report()
        benchmark.generate_latex_tables()
    elif args.reliability:
        benchmark.run_reliability_test(args.nodes, args.duration)
        benchmark.generate_report()
        benchmark.generate_latex_tables()
    else:
        # Default: quick benchmark
        print("No specific test selected. Running quick benchmark...")
        print("Use --help to see available options.\n")
        benchmark.iterations = QUICK_ITERATIONS
        benchmark.run_quick_benchmark()
    
    print("\n" + "=" * 70)
    print(f"Results saved to: {benchmark.output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
