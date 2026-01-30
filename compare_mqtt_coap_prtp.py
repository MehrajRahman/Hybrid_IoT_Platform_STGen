#!/usr/bin/env python3
"""
Quick 3-Protocol Comparison: MQTT vs CoAP vs PRTP

This is a simplified script to quickly compare the three protocols
for DCOSS paper preparation. For full benchmarks, use run_dcoss_benchmark.py

Usage:
    python compare_mqtt_coap_prtp.py [--nodes N] [--duration S]
    
Example:
    python compare_mqtt_coap_prtp.py --nodes 50 --duration 30
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from stgen.comparator import ProtocolComparator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
_LOG = logging.getLogger("compare")

# Three protocols for DCOSS
PROTOCOLS = ["mqtt", "coap", "prtp"]


def create_comparison_config(nodes: int = 50, duration: int = 30, 
                             rate_hz: float = 10.0) -> str:
    """Create a temporary scenario configuration."""
    config = {
        "name": f"DCOSS_Comparison_{nodes}nodes",
        "description": "MQTT vs CoAP vs PRTP comparison for DCOSS paper",
        "protocol": "placeholder",
        "mode": "active",
        "server_ip": "127.0.0.1",
        "server_port": 5000,
        "num_clients": nodes,
        "duration": duration,
        "sensors": ["temp"],
        "traffic_pattern": {
            "temp": {"rate_hz": rate_hz, "burst": False}
        },
        "packets_per_client": int(duration * rate_hz),
    }
    
    config_file = Path(f"temp_comparison_config.json")
    config_file.write_text(json.dumps(config, indent=2))
    return str(config_file)


def print_comparison_table(results: Dict[str, Dict[str, Any]]):
    """Print a nice comparison table."""
    print("\n" + "=" * 80)
    print("  DCOSS PROTOCOL COMPARISON RESULTS  ".center(80, "="))
    print("=" * 80)
    
    # Header
    print(f"\n{'Metric':<20} ", end="")
    for proto in PROTOCOLS:
        print(f"{proto.upper():^18}", end="")
    print("\n" + "-" * 80)
    
    metrics = [
        ("Messages Sent", "sent", "{:,.0f}"),
        ("Messages Received", "recv", "{:,.0f}"),
        ("Packet Loss", "loss", "{:.2%}"),
        ("Avg Latency (ms)", "lat_avg_ms", "{:.2f}"),
        ("P50 Latency (ms)", "lat_p50_ms", "{:.2f}"),
        ("P95 Latency (ms)", "lat_p95_ms", "{:.2f}"),
        ("P99 Latency (ms)", "lat_p99_ms", "{:.2f}"),
    ]
    
    for name, key, fmt in metrics:
        print(f"{name:<20} ", end="")
        for proto in PROTOCOLS:
            if proto in results and key in results[proto]:
                val = results[proto][key]
                print(f"{fmt.format(val):^18}", end="")
            else:
                print(f"{'N/A':^18}", end="")
        print()
    
    print("-" * 80)
    
    # Determine winner
    winner = determine_winner(results)
    print(f"\n🏆 BEST PROTOCOL: {winner['protocol'].upper()}")
    print(f"   Reason: {winner['reason']}")
    print("=" * 80)


def determine_winner(results: Dict[str, Dict]) -> Dict[str, str]:
    """Determine the best protocol based on multiple criteria."""
    scores = {}
    
    for proto in PROTOCOLS:
        if proto not in results or "error" in results.get(proto, {}):
            continue
        
        r = results[proto]
        score = 0
        
        # Lower latency is better (weight: 30%)
        lat = r.get("lat_p95_ms", 100)
        score += (100 - lat) * 0.3
        
        # Lower loss is better (weight: 40%)
        loss = r.get("loss", 1.0) * 100
        score += (100 - loss) * 0.4
        
        # Higher throughput is better (weight: 30%)
        recv = r.get("recv", 0)
        sent = r.get("sent", 1)
        delivery_rate = (recv / sent) if sent > 0 else 0
        score += delivery_rate * 30
        
        scores[proto] = score
    
    if not scores:
        return {"protocol": "None", "reason": "No valid results"}
    
    winner = max(scores, key=scores.get)
    r = results[winner]
    
    return {
        "protocol": winner,
        "reason": f"Latency P95: {r.get('lat_p95_ms', 0):.1f}ms, Loss: {r.get('loss', 0)*100:.2f}%, Delivered: {r.get('recv', 0):,}"
    }


def print_latex_table(results: Dict[str, Dict]):
    """Generate LaTeX table for paper."""
    print("\n% LaTeX table for DCOSS paper")
    print("\\begin{table}[htbp]")
    print("\\caption{Protocol Performance Comparison}")
    print("\\label{tab:protocol-comparison}")
    print("\\centering")
    print("\\begin{tabular}{lccc}")
    print("\\hline")
    print("\\textbf{Metric} & \\textbf{MQTT} & \\textbf{CoAP} & \\textbf{PRTP} \\\\")
    print("\\hline")
    
    metrics = [
        ("Latency Avg (ms)", "lat_avg_ms"),
        ("Latency P95 (ms)", "lat_p95_ms"),
        ("Packet Loss (\\%)", "loss"),
        ("Messages Delivered", "recv"),
    ]
    
    for name, key in metrics:
        row = [name]
        for proto in PROTOCOLS:
            if proto in results and key in results[proto]:
                val = results[proto][key]
                if key == "loss":
                    row.append(f"{val*100:.2f}")
                elif key == "recv":
                    row.append(f"{int(val):,}")
                else:
                    row.append(f"{val:.2f}")
            else:
                row.append("--")
        print(" & ".join(row) + " \\\\")
    
    print("\\hline")
    print("\\end{tabular}")
    print("\\end{table}")


def main():
    parser = argparse.ArgumentParser(
        description="Quick MQTT vs CoAP vs PRTP Comparison"
    )
    parser.add_argument("--nodes", type=int, default=50,
                        help="Number of sensor nodes (default: 50)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Test duration in seconds (default: 30)")
    parser.add_argument("--rate", type=float, default=10.0,
                        help="Message rate per node (Hz, default: 10)")
    parser.add_argument("--latex", action="store_true",
                        help="Also print LaTeX table")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("  DCOSS PROTOCOL COMPARISON: MQTT vs CoAP vs PRTP  ".center(80))
    print("=" * 80)
    print(f"Configuration:")
    print(f"  - Nodes: {args.nodes}")
    print(f"  - Duration: {args.duration}s")
    print(f"  - Rate: {args.rate} msg/s per node")
    print(f"  - Expected messages: {int(args.nodes * args.rate * args.duration):,}")
    print()
    
    # Create config
    config_file = create_comparison_config(
        nodes=args.nodes,
        duration=args.duration,
        rate_hz=args.rate
    )
    
    try:
        # Run comparison
        comparator = ProtocolComparator(config_file, PROTOCOLS)
        results = comparator.run_comparison()
        
        # Print results
        print_comparison_table(results)
        
        if args.latex:
            print_latex_table(results)
        
        # Save results
        output_file = f"dcoss_comparison_{args.nodes}nodes_{int(time.time())}.json"
        Path(output_file).write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to: {output_file}")
        
    finally:
        # Cleanup
        Path(config_file).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
