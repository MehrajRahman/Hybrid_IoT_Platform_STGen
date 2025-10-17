
#!/usr/bin/env python3
"""Generate graphs from STGen test results."""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Error: matplotlib and numpy required")
    print("Install with: pip install matplotlib numpy")
    sys.exit(1)


def load_results(result_dir: str) -> Dict[str, Any]:
    """Load results from directory."""
    summary_file = Path(result_dir) / "summary.json"
    
    if not summary_file.exists():
        raise FileNotFoundError(f"No summary.json in {result_dir}")
    
    return json.loads(summary_file.read_text())


def plot_latency_distribution(results: Dict[str, Any], output_file: str) -> None:
    """Plot latency distribution."""
    if "lat" not in results or not results["lat"]:
        print("Warning: No latency data")
        return
    
    fig, axes = plt.subplots