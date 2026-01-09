"""
@file generate_reports.py
@brief Batch Report Generator for STGen Results
@details Scans the results directory, computes advanced statistics (percentiles) from 
         raw latency files, and uses the ReportGenerator class to produce multi-format 
         reports (HTML, MD, CSV, TXT) for each test run found.
"""

import os
import json
import numpy as np
from report_generator import ReportGenerator

# @brief Root directory containing test result subfolders
RESULTS_ROOT = "results"


def load_latencies(lat_file):
    """
    @brief Load latencies from file and compute percentiles.
    
    @details Reads raw latency values (assumed to be in seconds) from a text file,
             converts them to milliseconds, and uses NumPy to calculate standard
             percentiles (p50, p75, p90, p95, p99).
             
    @param lat_file Path to the text file containing raw latency samples (one per line).
    @return Dict[str, float] Dictionary containing calculated percentiles and sample count.
            Returns an empty dict if the file cannot be read or is empty.
    """
    try:
        with open(lat_file) as f:
            latencies = [float(line.strip()) for line in f if line.strip()]
        if not latencies:
            return {}
        latencies_ms = [l * 1000 for l in latencies]  # convert sec -> ms

        return {
            "p50_ms": float(np.percentile(latencies_ms, 50)),
            "p75_ms": float(np.percentile(latencies_ms, 75)),
            "p90_ms": float(np.percentile(latencies_ms, 90)),
            "p95_ms": float(np.percentile(latencies_ms, 95)),
            "p99_ms": float(np.percentile(latencies_ms, 99)),
            "latency_samples": len(latencies)
        }
    except Exception as e:
        print(f" Could not process {lat_file}: {e}")
        return {}


def generate_reports():
    """
    @brief Main batch processing function.
    
    @details Iterates through all subdirectories in RESULTS_ROOT. For every folder 
             containing a 'summary.json':
             1. Loads the base summary.
             2. Calculates and merges advanced latency statistics (if 'latencies.txt' exists).
             3. Initializes a ReportGenerator.
             4. Generates reports in HTML, Markdown, CSV, and Text formats.
    
    @return None
    """
    for folder in sorted(os.listdir(RESULTS_ROOT)):
        folder_path = os.path.join(RESULTS_ROOT, folder)
        summary_path = os.path.join(folder_path, "summary.json")
        lat_file = os.path.join(folder_path, "latencies.txt")

        if not os.path.isdir(folder_path) or not os.path.exists(summary_path):
            continue

        try:
            with open(summary_path) as f:
                results = json.load(f)

            # augment results with latency stats if available
            if os.path.exists(lat_file):
                latency_stats = load_latencies(lat_file)
                results.update(latency_stats)

            protocol = results.get("protocol", folder.split("_")[0]).upper()
            scenario_name = f"{protocol} Test - {folder}"

            rg = ReportGenerator(results, scenario_name=scenario_name)

            print(f" Generating reports for {folder} ...")
            rg.generate_html_report(os.path.join(folder_path, "report.html"))
            rg.generate_markdown_report(os.path.join(folder_path, "report.md"))
            rg.generate_csv_report(os.path.join(folder_path, "report.csv"))
            rg.generate_text_report(os.path.join(folder_path, "report.txt"))
            print(f" Done: {folder}")

        except Exception as e:
            print(f" Error processing {folder}: {e}")


if __name__ == "__main__":
    generate_reports()
