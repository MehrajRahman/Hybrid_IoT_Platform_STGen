#!/usr/bin/env python3
"""
Simple test runner to demonstrate framework comparison
Usage: python3 run_test.py [scenario_name] [frameworks]
"""

import subprocess
import sys
import json
from pathlib import Path

def run_comparison(scenario="smart_home", frameworks="stgen"):
    """Run framework comparison."""
    
    print("\n" + "=" * 70)
    print(f"  STGen Framework Comparison: {scenario}")
    print("=" * 70)
    print(f"Scenario: {scenario}")
    print(f"Frameworks: {frameworks}")
    print()
    
    cmd = [
        "python3",
        "compare_frameworks.py",
        "--scenario", scenario,
        "--frameworks", frameworks,
        "--timeout", "300"
    ]
    
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "=" * 70)
        print("  Test Completed Successfully")
        print("=" * 70)
        
        # Try to display results
        if Path("framework_comparison.json").exists():
            print("\nResults saved to:")
            print("  - framework_comparison.md (Human-readable)")
            print("  - framework_comparison.json (Machine-readable)")
            print("\nView results with:")
            print("  cat framework_comparison.md")
    else:
        print(f"\n✗ Test failed with return code {result.returncode}")
        return 1
    
    return 0

def list_scenarios():
    """List available scenarios."""
    scenarios_dir = Path("configs/scenarios")
    if scenarios_dir.exists():
        scenarios = sorted([f.stem for f in scenarios_dir.glob("*.json")])
        return scenarios
    return []

def main():
    """Main entry point."""
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--list", "-l", "--help", "-h"]:
            print("STGen Framework Comparison Test Runner")
            print("\nUsage: python3 run_test.py [scenario] [frameworks]")
            print("\nDefault:")
            print("  Scenario: smart_home")
            print("  Frameworks: stgen")
            print("\nAvailable Scenarios:")
            scenarios = list_scenarios()
            for scenario in scenarios:
                print(f"  - {scenario}")
            print("\nExamples:")
            print("  python3 run_test.py smart_home stgen")
            print("  python3 run_test.py connected_vehicle stgen,gotham")
            print("  python3 run_test.py smart_agriculture stgen")
            return 0
    
    # Parse arguments
    scenario = sys.argv[1] if len(sys.argv) > 1 else "smart_home"
    frameworks = sys.argv[2] if len(sys.argv) > 2 else "stgen"
    
    # Validate scenario
    scenarios = list_scenarios()
    if scenario not in scenarios:
        print(f"✗ Unknown scenario: {scenario}")
        print(f"\nAvailable scenarios:")
        for s in scenarios:
            print(f"  - {s}")
        return 1
    
    return run_comparison(scenario, frameworks)

if __name__ == "__main__":
    sys.exit(main())
