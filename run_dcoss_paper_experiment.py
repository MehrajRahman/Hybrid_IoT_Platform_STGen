#!/usr/bin/env python3
"""
DCOSS Paper Experiment: Proper Comparison of MQTT, CoAP, and PRTP

This script runs a comprehensive benchmark for the DCOSS paper comparing:
- MQTT (with Mosquitto broker)
- CoAP (with aiocoap) 
- PRTP (PRIoTP with real C binaries)

The experiment includes:
1. Latency comparison (end-to-end message latency)
2. Throughput comparison (messages per second)
3. Scalability test (10-100 nodes)
4. Summary report generation

Author: STGen Framework
Date: 2026-01-27
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_experiment(experiment_name: str, args: list):
    """Run a single experiment and wait for completion."""
    print(f"\n{'='*70}")
    print(f"RUNNING: {experiment_name}")
    print(f"{'='*70}")
    
    cmd = [sys.executable, "run_dcoss_benchmark.py"] + args
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,  # Show output in real-time
            timeout=600  # 10 minute timeout per experiment
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"ERROR: {experiment_name} timed out!")
        return False
    except Exception as e:
        print(f"ERROR: {experiment_name} failed: {e}")
        return False


def generate_summary():
    """Generate a consolidated summary from all benchmark results."""
    results_dir = Path("results")
    dcoss_dirs = sorted(results_dir.glob("dcoss_benchmark_*"))
    
    if not dcoss_dirs:
        print("No DCOSS benchmark results found!")
        return
    
    # Use the most recent
    latest = dcoss_dirs[-1]
    report_file = latest / "benchmark_report.json"
    
    if not report_file.exists():
        print(f"No report found in {latest}")
        return
    
    with open(report_file) as f:
        results = json.load(f)
    
    print("\n" + "="*80)
    print("DCOSS PAPER EXPERIMENT SUMMARY")
    print("="*80)
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")
    print(f"Results directory: {latest}")
    
    # Print latency comparison
    if "latency_comparison" in results.get("experiments", {}):
        lat_data = results["experiments"]["latency_comparison"]["results"]
        print("\n--- LATENCY COMPARISON ---")
        print(f"{'Protocol':<10} {'Avg (ms)':<12} {'P50 (ms)':<12} {'P95 (ms)':<12} {'Loss %':<10}")
        print("-" * 60)
        for proto in ["mqtt", "coap", "prtp"]:
            if proto in lat_data:
                d = lat_data[proto]
                loss = d.get("loss", 0) * 100
                print(f"{proto.upper():<10} {d.get('lat_avg_ms', 0):<12.2f} {d.get('lat_p50_ms', 0):<12.2f} {d.get('lat_p95_ms', 0):<12.2f} {loss:<10.2f}")
    
    # Print throughput comparison
    if "throughput_comparison" in results.get("experiments", {}):
        tp_data = results["experiments"]["throughput_comparison"]["results"]
        print("\n--- THROUGHPUT COMPARISON ---")
        print(f"{'Protocol':<10} {'Sent':<10} {'Received':<12} {'Rate (msg/s)':<15}")
        print("-" * 50)
        for proto in ["mqtt", "coap", "prtp"]:
            if proto in tp_data:
                d = tp_data[proto]
                duration = d.get("duration", 1)
                if duration == 0:
                    duration = 1
                rate = d.get("recv", 0) / duration if duration else 0
                print(f"{proto.upper():<10} {d.get('sent', 0):<10} {d.get('recv', 0):<12} {rate:<15.1f}")
    
    print("\n" + "="*80)
    print("EXPERIMENT COMPLETE")
    print("="*80)


def main():
    print("="*80)
    print("DCOSS PAPER EXPERIMENT: MQTT vs CoAP vs PRTP")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Change to STGen directory
    os.chdir(Path(__file__).parent)
    
    experiments_completed = []
    
    # Run experiments with reasonable parameters for a paper
    
    # 1. Quick latency test (20 clients, 15s)
    if run_experiment("Quick Benchmark (Latency + Throughput)", ["--quick"]):
        experiments_completed.append("quick")
    
    # 2. Scalability test with moderate parameters
    # Note: This takes longer, uncomment for full benchmark
    # if run_experiment("Scalability Test", ["--scalability", "--duration", "20"]):
    #     experiments_completed.append("scalability")
    
    print(f"\n{'='*80}")
    print(f"Experiments completed: {', '.join(experiments_completed) if experiments_completed else 'None'}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Generate consolidated summary
    generate_summary()


if __name__ == "__main__":
    main()
