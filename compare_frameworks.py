#!/usr/bin/env python3
"""
Multi-Framework Comparison Tool
Compares STGen, Gotham, and GothX across identical IoT scenarios
"""

import json
import subprocess
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
_LOG = logging.getLogger("compare_frameworks")


@dataclass
class FrameworkConfig:
    """Configuration for a test framework."""
    name: str
    executable: str  # Command to run the framework
    config_path: str
    result_parser: callable  # Function to parse results
    supports_scenarios: bool = True
    timeout: int = 300  # seconds


class FrameworkComparator:
    """Coordinates comparison of multiple IoT testing frameworks."""
    
    def __init__(self, frameworks: List[FrameworkConfig], scenario_name: str):
        """
        Initialize comparator.
        
        Args:
            frameworks: List of framework configurations
            scenario_name: Scenario to test (e.g., 'smart_home')
        """
        self.frameworks = {fw.name: fw for fw in frameworks}
        self.scenario_name = scenario_name
        self.results: Dict[str, Dict[str, Any]] = {}
        self.comparison_timestamp = datetime.now().isoformat()
        
        _LOG.info(f"Initialized comparator for scenario: {scenario_name}")
        _LOG.info(f"Frameworks: {', '.join(self.frameworks.keys())}")
    
    def run_all_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all frameworks on the same scenario.
        
        Returns:
            Dict mapping framework name to results
        """
        for fw_name, fw_config in self.frameworks.items():
            _LOG.info("=" * 70)
            _LOG.info(f"Running: {fw_name}")
            _LOG.info("=" * 70)
            
            try:
                result = self._run_framework(fw_config)
                self.results[fw_name] = result
                _LOG.info(f"✓ {fw_name} completed successfully")
            except Exception as e:
                _LOG.error(f"✗ {fw_name} failed: {e}")
                self.results[fw_name] = {"error": str(e)}
            
            # Cool-down between frameworks
            time.sleep(2)
        
        return self.results
    
    def _run_framework(self, fw: FrameworkConfig) -> Dict[str, Any]:
        """
        Execute a single framework test.
        
        Args:
            fw: Framework configuration
            
        Returns:
            Parsed results dictionary
        """
        if fw.name == "stgen":
            return self._run_stgen(fw)
        elif fw.name == "gotham":
            return self._run_gotham(fw)
        elif fw.name == "gothx":
            return self._run_gothx(fw)
        else:
            raise ValueError(f"Unknown framework: {fw.name}")
    
    def _run_stgen(self, fw: FrameworkConfig) -> Dict[str, Any]:
        """Run STGen framework."""
        cmd = [
            "python3", "-m", "stgen.main",
            "--scenario", self.scenario_name,
            "--validate"
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=fw.timeout)
            elapsed = time.time() - start_time
            
            if result.returncode != 0:
                _LOG.warning(f"STGen exited with code {result.returncode}")
                _LOG.warning(f"stderr: {result.stderr}")
            
            # Parse STGen results from results directory
            results = self._parse_stgen_results(self.scenario_name)
            results["execution_time"] = elapsed
            results["framework"] = "stgen"
            return results
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"STGen timed out after {fw.timeout}s")
    
    def _run_gotham(self, fw: FrameworkConfig) -> Dict[str, Any]:
        """Run Gotham framework using GothamAdapter."""
        from framework_adapters import GothamAdapter
        
        start_time = time.time()
        try:
            adapter = GothamAdapter(timeout=fw.timeout)
            result = adapter.run_scenario(self.scenario_name)
            elapsed = time.time() - start_time
            
            result["execution_time"] = elapsed
            result["framework"] = "gotham"
            
            if "error" in result:
                _LOG.error(f"Gotham error: {result['error']}")
            
            return result
            
        except Exception as e:
            _LOG.error(f"Gotham execution failed: {e}")
            return {
                "error": str(e),
                "framework": "gotham",
                "execution_time": time.time() - start_time
            }
    
    def _run_gothx(self, fw: FrameworkConfig) -> Dict[str, Any]:
        """
        Run GothX framework.
        
        Note: GothX is currently a placeholder. To integrate a real framework:
        1. Identify the actual framework/tool
        2. Update this method with its CLI/API
        3. Create an adapter similar to GothamAdapter
        """
        return {
            "error": "GothX not yet integrated",
            "message": "GothX placeholder - awaiting framework specification",
            "status": "not_implemented",
            "framework": "gothx"
        }
    
    def _parse_stgen_results(self, scenario: str) -> Dict[str, Any]:
        """Parse STGen results from results directory."""
        results_dir = Path("results")
        
        # Find latest result directory for this scenario
        matching_dirs = list(results_dir.glob(f"*{scenario}*"))
        if not matching_dirs:
            _LOG.warning(f"No results found for scenario: {scenario}")
            return {"error": "No results found"}
        
        latest_dir = sorted(matching_dirs)[-1]
        summary_file = latest_dir / "summary.json"
        
        if not summary_file.exists():
            return {"error": f"Summary file not found: {summary_file}"}
        
        try:
            with open(summary_file) as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to parse summary: {e}"}
    
    def generate_comparison_report(self, output_file: str = "framework_comparison.md") -> str:
        """
        Generate comprehensive comparison report.
        
        Args:
            output_file: Where to save the report
            
        Returns:
            Report content
        """
        if not self.results:
            raise ValueError("No results to compare. Run frameworks first.")
        
        report_lines = []
        
        # Header
        report_lines.append("# IoT Framework Comparison Report")
        report_lines.append(f"\n**Scenario:** {self.scenario_name}")
        report_lines.append(f"**Date:** {self.comparison_timestamp}")
        report_lines.append(f"**Frameworks:** {', '.join(self.frameworks.keys())}\n")
        
        # Executive Summary
        report_lines.append("## Executive Summary\n")
        report_lines.append("| Framework | Status | Execution Time (s) |")
        report_lines.append("|-----------|--------|-------------------|")
        
        for fw_name, result in self.results.items():
            status = "✓ Pass" if "error" not in result else "✗ Fail"
            exec_time = result.get("execution_time", "N/A")
            report_lines.append(f"| {fw_name} | {status} | {exec_time} |")
        
        report_lines.append("")
        
        # Detailed Metrics Comparison
        report_lines.append("## Metrics Comparison\n")
        
        # Extract common metrics
        all_metrics = self._extract_common_metrics()
        
        if all_metrics:
            # Create comparison table
            report_lines.append("| Metric | " + " | ".join(self.frameworks.keys()) + " |")
            report_lines.append("|--------|" + "|".join(["---"] * (len(self.frameworks) + 1)) + "|")
            
            for metric in sorted(all_metrics):
                row = [metric]
                for fw_name in self.frameworks.keys():
                    value = self.results[fw_name].get(metric, "N/A")
                    if isinstance(value, float):
                        row.append(f"{value:.3f}")
                    else:
                        row.append(str(value))
                report_lines.append("| " + " | ".join(row) + " |")
            
            report_lines.append("")
        
        # Per-Framework Details
        report_lines.append("## Framework Details\n")
        
        for fw_name, result in self.results.items():
            report_lines.append(f"### {fw_name.upper()}\n")
            
            if "error" in result:
                report_lines.append(f"**Error:** {result['error']}\n")
            else:
                report_lines.append("```json")
                report_lines.append(json.dumps(result, indent=2))
                report_lines.append("```\n")
        
        # Winner Analysis
        report_lines.append("## Winner Analysis\n")
        report_lines.append(self._calculate_winners())
        
        report_content = "\n".join(report_lines)
        
        # Save report
        with open(output_file, "w") as f:
            f.write(report_content)
        
        _LOG.info(f"Report saved to {output_file}")
        return report_content
    
    def _extract_common_metrics(self) -> set:
        """Extract metrics that appear in all results."""
        if not self.results:
            return set()
        
        common_metrics = None
        for result in self.results.values():
            if "error" in result:
                continue
            
            result_metrics = {k for k in result.keys() 
                            if k not in ["framework", "execution_time", "error"]}
            
            if common_metrics is None:
                common_metrics = result_metrics
            else:
                common_metrics &= result_metrics
        
        return common_metrics or set()
    
    def _calculate_winners(self) -> str:
        """Determine winning framework for key metrics."""
        output = []
        
        metrics_to_score = {
            "latency": ["lat_avg_ms", "lat_p95_ms"],
            "throughput": ["sent", "recv"],
            "reliability": ["loss"],
            "energy": ["power_mw", "energy_mj"]
        }
        
        for category, metric_names in metrics_to_score.items():
            output.append(f"\n### {category.capitalize()}\n")
            
            for metric_name in metric_names:
                candidates = {}
                
                for fw_name, result in self.results.items():
                    if "error" not in result and metric_name in result:
                        candidates[fw_name] = result[metric_name]
                
                if not candidates:
                    output.append(f"**{metric_name}:** No data")
                    continue
                
                # Determine "best" based on metric type
                if "loss" in metric_name or "power" in metric_name or "energy" in metric_name or "lat" in metric_name:
                    # Lower is better
                    best_fw = min(candidates, key=candidates.get)
                    output.append(f"**{metric_name}:** {best_fw} ({candidates[best_fw]})")
                else:
                    # Higher is better
                    best_fw = max(candidates, key=candidates.get)
                    output.append(f"**{metric_name}:** {best_fw} ({candidates[best_fw]})")
        
        return "\n".join(output)
    
    def generate_json_summary(self, output_file: str = "comparison_summary.json") -> None:
        """Save results as JSON for programmatic analysis."""
        summary = {
            "timestamp": self.comparison_timestamp,
            "scenario": self.scenario_name,
            "frameworks": list(self.frameworks.keys()),
            "results": self.results
        }
        
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        _LOG.info(f"JSON summary saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare IoT testing frameworks (STGen vs Gotham vs GothX)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare on smart_home scenario
  python compare_frameworks.py --scenario smart_home
  
  # Specify which frameworks to compare
  python compare_frameworks.py --scenario smart_agriculture --frameworks stgen,gotham
  
  # Use custom timeout
  python compare_frameworks.py --scenario smart_home --timeout 600
        """
    )
    
    parser.add_argument("--scenario", default="smart_home",
                       help="Scenario to test (default: smart_home)")
    parser.add_argument("--frameworks", default="stgen,gotham",
                       help="Comma-separated frameworks to compare (default: stgen,gotham)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout per framework in seconds (default: 300)")
    parser.add_argument("--output", default="framework_comparison.md",
                       help="Output report file (default: framework_comparison.md)")
    parser.add_argument("--gotham-path", default=None,
                       help="Path to Gotham repository (auto-detected if not specified)")
    parser.add_argument("--list-frameworks", action="store_true",
                       help="List available frameworks and exit")
    
    args = parser.parse_args()
    
    # Handle list-frameworks flag
    if args.list_frameworks:
        from framework_adapters import print_framework_status
        print_framework_status()
        return 0
    
    # Configure frameworks
    frameworks = []
    
    fw_configs = {
        "stgen": FrameworkConfig(
            name="stgen",
            executable="python -m stgen.main",
            config_path="configs/scenarios/",
            result_parser=lambda: None,
            timeout=args.timeout
        ),
        "gotham": FrameworkConfig(
            name="gotham",
            executable="gotham",  # Uses GothamAdapter internally
            config_path="gotham_config/",
            result_parser=lambda: None,
            timeout=args.timeout
        ),
        "gothx": FrameworkConfig(
            name="gothx",
            executable="gothx",  # Placeholder - specify actual framework
            config_path="gothx_config/",
            result_parser=lambda: None,
            timeout=args.timeout
        )
    }
    
    requested_frameworks = [fw.strip() for fw in args.frameworks.split(",")]
    for fw_name in requested_frameworks:
        if fw_name in fw_configs:
            frameworks.append(fw_configs[fw_name])
        else:
            _LOG.warning(f"Unknown framework: {fw_name}")
    
    if not frameworks:
        _LOG.error("No valid frameworks specified")
        return 1
    
    # Run comparison
    comparator = FrameworkComparator(frameworks, args.scenario)
    comparator.run_all_frameworks()
    
    # Generate reports
    comparator.generate_comparison_report(args.output)
    comparator.generate_json_summary(args.output.replace(".md", ".json"))
    
    print(f"\n✓ Comparison complete!")
    print(f"  Markdown report: {args.output}")
    print(f"  JSON summary: {args.output.replace('.md', '.json')}")
    
    return 0


if __name__ == "__main__":
    exit(main())
