#!/usr/bin/env python3
"""
Quick validation script to check framework setup and generate test comparison
"""

import subprocess
import sys
import json
from pathlib import Path

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def check_stgen():
    """Check STGen installation."""
    print_header("STGen Status")
    
    try:
        result = subprocess.run(
            ["python3", "-m", "stgen.main", "--help"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ STGen is installed and accessible")
            
            # List available scenarios
            try:
                result = subprocess.run(
                    ["python3", "-m", "stgen.main", "--list-scenarios"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "smart_home" in result.stdout:
                    print("✓ STGen scenarios are available")
            except:
                pass
            
            return True
        else:
            print("✗ STGen is not working properly")
            print(f"  Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ STGen check timed out")
        return False
    except FileNotFoundError:
        print("✗ STGen executable not found")
        return False
    except Exception as e:
        print(f"✗ Error checking STGen: {e}")
        return False

def check_gotham():
    """Check Gotham installation."""
    print_header("Gotham Status")
    
    try:
        from framework_adapters import GothamAdapter
        
        adapter = GothamAdapter()
        installed = adapter.validate_installation()
        
        if installed:
            print("✓ Gotham is installed and verified")
            info = adapter.get_info()
            print(f"  Location: {info['repo_path']}")
            print(f"  Version: GNS3-based emulation platform")
            print(f"  Note: Requires GNS3 server to be running for tests")
            return True
        else:
            print("✗ Gotham is not properly installed")
            print(f"  Looking in: {adapter.repo_path}")
            print(f"\n  Install from: https://github.com/xsaga/gotham-iot-testbed")
            return False
    except Exception as e:
        print(f"✗ Error checking Gotham: {e}")
        return False

def check_framework_comparison_tool():
    """Check comparison tool setup."""
    print_header("Framework Comparison Tool")
    
    compare_script = Path("compare_frameworks.py")
    if compare_script.exists():
        print("✓ Comparison script found: compare_frameworks.py")
        return True
    else:
        print("✗ Comparison script not found")
        return False

def check_scenarios():
    """Check available scenarios."""
    print_header("Available Scenarios")
    
    scenarios_dir = Path("configs/scenarios")
    if not scenarios_dir.exists():
        print("✗ Scenarios directory not found")
        return False
    
    scenarios = sorted([f.stem for f in scenarios_dir.glob("*.json")])
    
    if scenarios:
        print(f"✓ Found {len(scenarios)} scenarios:")
        for scenario in scenarios:
            print(f"  - {scenario}")
        return True
    else:
        print("✗ No scenarios found")
        return False

def test_stgen_quick(scenario="smart_home"):
    """Run a quick STGen test."""
    print_header(f"Quick STGen Test: {scenario}")
    
    try:
        print(f"Running STGen on {scenario} scenario...")
        result = subprocess.run(
            ["python", "-m", "stgen.main", "--scenario", scenario, "--duration", "5"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ STGen test completed successfully")
            
            # Check for results
            results_dirs = list(Path("results").glob("*"))
            if results_dirs:
                latest = sorted(results_dirs)[-1]
                print(f"  Results saved to: {latest}")
                
                summary_file = latest / "summary.json"
                if summary_file.exists():
                    with open(summary_file) as f:
                        summary = json.load(f)
                    print(f"  Protocol: {summary.get('protocol', 'unknown')}")
                    print(f"  Packets sent: {summary.get('sent', 'N/A')}")
                    print(f"  Packet loss: {summary.get('loss', 'N/A')}")
            
            return True
        else:
            print("✗ STGen test failed")
            print(f"  Error: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ STGen test timed out")
        return False
    except Exception as e:
        print(f"✗ Error running STGen test: {e}")
        return False

def generate_setup_report():
    """Generate setup status report."""
    print_header("Setup Summary")
    
    results = {
        "stgen": check_stgen(),
        "gotham": check_gotham(),
        "comparison_tool": check_framework_comparison_tool(),
        "scenarios": check_scenarios(),
    }
    
    print_header("Overall Status")
    
    all_ok = all(results.values())
    
    for component, status in results.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {component.replace('_', ' ').title()}")
    
    if all_ok:
        print("\n✓ All components are ready!")
        print("\nNext steps:")
        print("  1. Run a framework comparison:")
        print("     python compare_frameworks.py --scenario smart_home")
        print("\n  2. View available frameworks:")
        print("     python framework_adapters.py")
        print("\n  3. See comparison results:")
        print("     cat framework_comparison.md")
    else:
        print("\n⚠ Some components need attention")
        print("\nTo install Gotham (optional):")
        print("  git clone https://github.com/xsaga/gotham-iot-testbed.git")
        print("  cd gotham-iot-testbed")
        print("  python3 -m venv venv && source venv/bin/activate")
        print("  pip install -r requirements.txt && make")
    
    return all_ok

def main():
    """Run all checks."""
    print("\n" + "█" * 70)
    print("  IoT Framework Comparison Tool - Setup Validation")
    print("█" * 70)
    
    print("\nChecking framework installation...")
    
    check_framework_comparison_tool()
    check_stgen()
    check_gotham()
    check_scenarios()
    
    # Optional: Quick test
    print_header("Running Quick STGen Test")
    print("(This requires Mosquitto broker to be running)")
    print("\nSkipping quick test - run manually with:")
    print("  python compare_frameworks.py --scenario smart_home --timeout 60")
    
    # Generate report
    all_ok = generate_setup_report()
    
    print("\n" + "█" * 70 + "\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
