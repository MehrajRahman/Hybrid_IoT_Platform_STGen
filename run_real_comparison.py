#!/usr/bin/env python3
"""
REAL Protocol Comparison with Network Emulation

This script runs ACTUAL protocol traffic through simulated network conditions
using Linux Traffic Control (tc) or application-level delays.

IMPORTANT: This runs REAL MQTT, CoAP, and PRTP traffic!

Requirements:
- For tc-based network emulation: sudo privileges
- For app-level emulation: no special privileges needed

Usage:
    # Without network emulation (baseline)
    python run_real_comparison.py --nodes 10 --duration 15

    # With application-level delay simulation
    python run_real_comparison.py --nodes 10 --duration 15 --delay 50 --loss 1

    # With tc network emulation (requires sudo)
    sudo python run_real_comparison.py --nodes 10 --duration 15 --use-tc --delay 50 --loss 1
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
_LOG = logging.getLogger("real_comparison")


def check_tc_available() -> bool:
    """Check if tc (traffic control) is available."""
    try:
        result = subprocess.run(["tc", "-V"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def apply_tc_netem(interface: str, delay_ms: int, loss_percent: float, jitter_ms: int = 0) -> bool:
    """
    Apply network emulation using tc netem.
    Requires root privileges.
    """
    try:
        # Remove existing qdisc first
        subprocess.run(
            ["tc", "qdisc", "del", "dev", interface, "root"],
            capture_output=True
        )
        
        # Build netem command
        cmd = ["tc", "qdisc", "add", "dev", interface, "root", "netem"]
        
        if delay_ms > 0:
            cmd.extend(["delay", f"{delay_ms}ms"])
            if jitter_ms > 0:
                cmd.extend([f"{jitter_ms}ms"])
        
        if loss_percent > 0:
            cmd.extend(["loss", f"{loss_percent}%"])
        
        _LOG.info(f"Applying tc netem: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            _LOG.error(f"tc failed: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        _LOG.error(f"Failed to apply tc netem: {e}")
        return False


def remove_tc_netem(interface: str) -> None:
    """Remove tc netem rules."""
    try:
        subprocess.run(
            ["tc", "qdisc", "del", "dev", interface, "root"],
            capture_output=True
        )
        _LOG.info(f"Removed tc netem from {interface}")
    except Exception as e:
        _LOG.warning(f"Failed to remove tc netem: {e}")


def run_protocol_test(
    protocol: str,
    nodes: int,
    duration: int,
    app_delay_ms: int = 0
) -> Dict[str, Any]:
    """
    Run actual protocol test using STGen.
    
    Args:
        protocol: mqtt, coap, or prtp
        nodes: Number of client nodes
        duration: Test duration in seconds
        app_delay_ms: Application-level delay to simulate (if not using tc)
    """
    # Create config file
    config = {
        "name": f"real_test_{protocol}",
        "protocol": protocol,
        "mode": "active",
        "server_ip": "127.0.0.1",
        "server_port": 5000 if protocol != "mqtt" else 1883,
        "sensor_port": 5000,
        "client_port": 5001,
        "num_clients": nodes,
        "duration": duration,
        "sensors": ["temp"],
        "traffic_pattern": {
            "temp": {"rate_hz": 10.0, "burst": False}
        },
        "packets_per_client": duration * 10,
    }
    
    # Add app-level delay if specified
    if app_delay_ms > 0:
        config["simulated_delay_ms"] = app_delay_ms
    
    config_file = Path(f"temp_real_{protocol}_config.json")
    config_file.write_text(json.dumps(config, indent=2))
    
    _LOG.info(f"Running {protocol.upper()} test: {nodes} nodes, {duration}s...")
    start_time = time.time()
    
    try:
        # Run the actual test
        result = subprocess.run(
            [sys.executable, "-m", "stgen.main", str(config_file)],
            capture_output=True,
            text=True,
            timeout=duration + 60  # Allow extra time for setup/teardown
        )
        
        elapsed = time.time() - start_time
        
        # Parse results from output
        output = result.stdout + result.stderr
        
        # Extract metrics from output
        metrics = {
            "protocol": protocol,
            "nodes": nodes,
            "duration": duration,
            "elapsed_time": elapsed,
            "success": result.returncode == 0,
        }
        
        # Parse sent/recv from output
        for line in output.split('\n'):
            if 'Sent:' in line and 'Recv:' in line:
                parts = line.split(',')
                for part in parts:
                    if 'Sent:' in part:
                        try:
                            metrics['sent'] = int(part.split(':')[1].strip())
                        except:
                            pass
                    if 'Recv:' in part:
                        try:
                            metrics['recv'] = int(part.split(':')[1].strip())
                        except:
                            pass
                    if 'Loss:' in part:
                        try:
                            loss_str = part.split(':')[1].strip().replace('%', '')
                            metrics['loss_percent'] = float(loss_str)
                        except:
                            pass
            
            if 'Latency:' in line and 'avg=' in line:
                try:
                    # Parse: Latency: avg=0.84ms, p50=0.80ms
                    parts = line.split('avg=')[1].split(',')
                    metrics['latency_avg_ms'] = float(parts[0].replace('ms', ''))
                    if 'p50=' in line:
                        metrics['latency_p50_ms'] = float(line.split('p50=')[1].split('ms')[0])
                except:
                    pass
        
        # Load detailed results if available
        results_dir = Path("results")
        if results_dir.exists():
            latest_results = sorted(results_dir.glob(f"{protocol}_*"), key=os.path.getmtime)
            if latest_results:
                summary_file = latest_results[-1] / "summary.json"
                if summary_file.exists():
                    detailed = json.loads(summary_file.read_text())
                    metrics.update({
                        'sent': detailed.get('sent', metrics.get('sent', 0)),
                        'recv': detailed.get('recv', metrics.get('recv', 0)),
                        'loss_percent': detailed.get('loss', 0) * 100,
                        'latency_avg_ms': detailed.get('lat_avg_ms', 0),
                        'latency_p50_ms': detailed.get('lat_p50_ms', 0),
                        'latency_p95_ms': detailed.get('lat_p95_ms', 0),
                    })
        
        return metrics
        
    except subprocess.TimeoutExpired:
        _LOG.error(f"{protocol} test timed out")
        return {"protocol": protocol, "error": "timeout"}
    except Exception as e:
        _LOG.error(f"{protocol} test failed: {e}")
        return {"protocol": protocol, "error": str(e)}
    finally:
        # Cleanup
        if config_file.exists():
            config_file.unlink()


def print_results_table(results: Dict[str, Dict], condition_desc: str):
    """Print formatted results table."""
    print(f"\n{'='*80}")
    print(f"  REAL PROTOCOL TEST RESULTS - {condition_desc}")
    print(f"{'='*80}")
    
    headers = ["Metric", "MQTT", "CoAP", "PRTP"]
    print(f"\n{headers[0]:<25} {headers[1]:^18} {headers[2]:^18} {headers[3]:^18}")
    print("-" * 80)
    
    metrics = [
        ("Messages Sent", "sent", "{:,}"),
        ("Messages Received", "recv", "{:,}"),
        ("Packet Loss (%)", "loss_percent", "{:.2f}"),
        ("Avg Latency (ms)", "latency_avg_ms", "{:.2f}"),
        ("P50 Latency (ms)", "latency_p50_ms", "{:.2f}"),
        ("P95 Latency (ms)", "latency_p95_ms", "{:.2f}"),
        ("Test Duration (s)", "elapsed_time", "{:.1f}"),
    ]
    
    for name, key, fmt in metrics:
        values = []
        for proto in ["mqtt", "coap", "prtp"]:
            if proto in results and key in results[proto]:
                val = results[proto][key]
                if val is not None:
                    values.append(fmt.format(val))
                else:
                    values.append("N/A")
            else:
                values.append("ERROR" if proto in results and "error" in results[proto] else "N/A")
        
        print(f"{name:<25} {values[0]:^18} {values[1]:^18} {values[2]:^18}")
    
    print("-" * 80)
    
    # Determine winner based on actual data
    valid_protos = [p for p in ["mqtt", "coap", "prtp"] if p in results and "error" not in results[p]]
    if valid_protos:
        # Best latency
        best_lat = min(valid_protos, key=lambda p: results[p].get("latency_p95_ms", float('inf')))
        # Best delivery
        best_del = max(valid_protos, key=lambda p: results[p].get("recv", 0))
        
        print(f"\n🏆 ACTUAL RESULTS:")
        print(f"   Lowest P95 Latency: {best_lat.upper()} ({results[best_lat].get('latency_p95_ms', 'N/A'):.2f}ms)")
        print(f"   Most Messages Delivered: {best_del.upper()} ({results[best_del].get('recv', 0):,})")
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Real Protocol Comparison")
    parser.add_argument("--nodes", type=int, default=10, help="Number of client nodes")
    parser.add_argument("--duration", type=int, default=15, help="Test duration in seconds")
    parser.add_argument("--delay", type=int, default=0, help="Network delay in ms")
    parser.add_argument("--loss", type=float, default=0, help="Packet loss percentage")
    parser.add_argument("--jitter", type=int, default=0, help="Delay jitter in ms")
    parser.add_argument("--use-tc", action="store_true", help="Use tc netem (requires sudo)")
    parser.add_argument("--interface", default="lo", help="Network interface for tc")
    parser.add_argument("--protocols", nargs="+", default=["mqtt", "coap", "prtp"],
                       help="Protocols to test")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  REAL PROTOCOL COMPARISON - ACTUAL TRAFFIC")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Nodes: {args.nodes}")
    print(f"  Duration: {args.duration}s")
    print(f"  Network Delay: {args.delay}ms")
    print(f"  Packet Loss: {args.loss}%")
    print(f"  Using tc netem: {args.use_tc}")
    
    # Apply network emulation if requested
    tc_applied = False
    if args.use_tc and (args.delay > 0 or args.loss > 0):
        if os.geteuid() != 0:
            _LOG.error("tc netem requires root privileges. Use sudo or --no-tc")
            print("\n⚠️  To use tc network emulation, run with sudo:")
            print(f"    sudo {sys.executable} {' '.join(sys.argv)}")
            print("\n  Or use application-level simulation (no sudo needed):")
            print(f"    {sys.executable} run_real_comparison.py --nodes {args.nodes} --delay {args.delay}")
            return
        
        if not check_tc_available():
            _LOG.error("tc command not available")
            return
        
        tc_applied = apply_tc_netem(args.interface, args.delay, args.loss, args.jitter)
        if not tc_applied:
            _LOG.error("Failed to apply tc netem")
            return
    
    try:
        # Run tests for each protocol
        results = {}
        
        for protocol in args.protocols:
            print(f"\n{'='*60}")
            _LOG.info(f"Testing {protocol.upper()}...")
            print(f"{'='*60}")
            
            result = run_protocol_test(
                protocol=protocol,
                nodes=args.nodes,
                duration=args.duration,
                app_delay_ms=args.delay if not args.use_tc else 0
            )
            results[protocol] = result
            
            if "error" in result:
                _LOG.error(f"{protocol.upper()} failed: {result['error']}")
            else:
                _LOG.info(f"{protocol.upper()} complete: sent={result.get('sent', 'N/A')}, recv={result.get('recv', 'N/A')}")
            
            # Small delay between tests
            time.sleep(2)
        
        # Build condition description
        if args.delay > 0 or args.loss > 0:
            condition = f"Delay={args.delay}ms, Loss={args.loss}%"
        else:
            condition = "Baseline (localhost)"
        
        print_results_table(results, condition)
        
        # Save results
        output_file = Path(f"real_comparison_{int(time.time())}.json")
        output_file.write_text(json.dumps(results, indent=2, default=str))
        print(f"\nResults saved to: {output_file}")
        
    finally:
        # Remove tc rules if applied
        if tc_applied:
            remove_tc_netem(args.interface)


if __name__ == "__main__":
    main()
