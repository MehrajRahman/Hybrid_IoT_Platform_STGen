#!/usr/bin/env python3
"""
Quick results visualization using matplotlib.
Usage: python tools/plot_results.py results/coap_1234567890/
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt


def plot_results(result_dir):
    """Plot latency distribution and summary."""
    result_dir = Path(result_dir)
    
    # Load summary
    summary_file = result_dir / "summary.json"
    if not summary_file.exists():
        print(f"Error: {summary_file} not found")
        return
    
    with open(summary_file) as f:
        summary = json.load(f)
    
    # Load latencies
    lat_file = result_dir / "latencies.txt"
    if not lat_file.exists():
        print(f"Error: {lat_file} not found")
        return
    
    latencies = [float(line.strip()) for line in lat_file.read_text().splitlines()]
    
    # Create plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Histogram
    ax1.hist(latencies, bins=50, edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Latency (ms)')
    ax1.set_ylabel('Count')
    ax1.set_title('Latency Distribution')
    ax1.grid(True, alpha=0.3)
    
    # Summary stats
    stats_text = f"""
Protocol: {summary['protocol']}
Mode: {summary['mode']}
Packets Sent: {summary['sent']}
Packets Received: {summary['recv']}
Packet Loss: {summary['loss']*100:.2f}%

Latency (ms):
  Avg: {summary.get('lat_avg_ms', 'N/A')}
  Min: {summary.get('lat_min_ms', 'N/A')}
  Max: {summary.get('lat_max_ms', 'N/A')}
  P50: {summary.get('lat_p50_ms', 'N/A')}
  P95: {summary.get('lat_p95_ms', 'N/A')}
    """.strip()
    
    ax2.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
             verticalalignment='center')
    ax2.axis('off')
    ax2.set_title('Summary Statistics')
    
    plt.tight_layout()
    
    # Save plot
    plot_file = result_dir / "latency_plot.png"
    plt.savefig(plot_file, dpi=150)
    print(f"Plot saved to {plot_file}")
    
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tools/plot_results.py <result_directory>")
        sys.exit(1)
    
    plot_results(sys.argv[1])