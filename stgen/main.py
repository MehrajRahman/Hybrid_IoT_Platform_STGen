"""
@file main.py
@brief STGen CLI Entry Point - Enhanced Version
@details This is the main entry point for the STGen IoT Protocol Testing Framework. 
         It handles command-line argument parsing, configuration loading, network emulation 
         setup, and orchestrates either single protocol tests or multi-protocol comparisons.

@author Mahdin Islam Ohi
@date 2026-01-08
@version 2.0

Usage: 
  python -m stgen.main <config.json>
  python -m stgen.main --scenario smart_home --protocol YOUR_PROTOCOL
  python -m stgen.main --compare coap,srtp --scenario industrial_iot
"""

import json
import logging
import sys
import time
import argparse
from pathlib import Path

from .orchestrator import Orchestrator
from .sensor_generator import generate_sensor_stream
from .utils import load_config, load_scenario, list_available_scenarios, list_available_protocols
from .failure_injector import FailureInjector
from .validator import validate_protocol_results
from .network_emulator import NetworkEmulator

## @brief Configure global logging settings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)

## @brief Logger instance for the main module
_LOG = logging.getLogger("stgen.main")


def parse_arguments():
    """
    @brief Parse command line arguments.
    
    @details Configures the ArgumentParser with options for configuration files, 
             scenarios, protocols, comparison modes, and utility flags like listing 
             resources or enabling debug mode.

    @return argparse.Namespace The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="STGen - IoT Protocol Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            # Run with config file
            python -m stgen.main configs/coap.json
            
            # Run with scenario
            python -m stgen.main --scenario smart_home --protocol coap
            
            # Compare protocols
            python -m stgen.main --compare coap,srtp --scenario industrial_iot
            
            # List available scenarios
            python -m stgen.main --list-scenarios
            
            # List available protocols
            python -m stgen.main --list-protocols
        """
    )
    
    parser.add_argument("config", nargs="?", help="Path to configuration file")
    parser.add_argument("--scenario", help="Use predefined scenario (e.g., smart_home)")
    parser.add_argument("--protocol", help="Protocol to test")
    parser.add_argument("--compare", help="Comma-separated list of protocols to compare")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios")
    parser.add_argument("--list-protocols", action="store_true", help="List available protocols")
    parser.add_argument("--validate", action="store_true", help="Run validation checks on results")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()


def list_scenarios():
    """
    @brief Print available scenarios to stdout.
    
    @details Scans the 'configs/scenarios/' directory via list_available_scenarios()
             and prints the name and description of each found scenario.
    
    @return None
    """
    scenarios = list_available_scenarios()
    if not scenarios:
        print("No scenarios found in configs/scenarios/")
        return
    
    print("\n Available Scenarios:")
    print("=" * 60)
    for scenario in sorted(scenarios):
        try:
            cfg = load_scenario(scenario)
            name = cfg.get("name", scenario)
            desc = cfg.get("description", "No description")
            print(f"\n  {scenario}")
            print(f"    Name: {name}")
            print(f"    Description: {desc}")
        except Exception as e:
            print(f"  {scenario} (error loading: {e})")
    print()


def list_protocols():
    """
    @brief Print available protocols to stdout.
    
    @details Scans the 'protocols/' directory via list_available_protocols()
             and lists them.
    
    @return None
    """
    protocols = list_available_protocols()
    if not protocols:
        print("No protocols found in protocols/")
        return
    
    print("\n Available Protocols:")
    print("=" * 60)
    for protocol in sorted(protocols):
        print(f"   {protocol}")
    print()


def run_single_test(cfg: dict) -> bool:
    """
    @brief Run a single protocol test.
    
    @details Performs the following lifecycle:
             1. Validates configuration.
             2. Sets up Network Emulator (if profile exists).
             3. Initializes the Orchestrator.
             4. Generates the sensor data stream.
             5. Runs the test.
             6. Cleans up network emulation and protocol resources.
             7. Saves the report if data was transmitted.

    @param cfg Dictionary containing the full test configuration.
    @return bool True if the test completed successfully and report was saved, False otherwise.
    
    @exception KeyboardInterrupt Handled to allow graceful cleanup during user interruption.
    @exception Exception Catch-all for runtime errors during test execution.
    """
    # Validate config
    from .utils import validate_config
    validate_config(cfg)
    
    _LOG.info(f"Loaded config from {cfg.get('_source', 'dict')}")
    
    # --- Define variables ---
    emulator = None
    orch = None
    ok = False
    
    try:
        # --- 1. START NETWORK EMULATOR ---
        if "network_profile" in cfg:
            profile_name = cfg['network_profile']
            _LOG.info(f"Applying network profile: {profile_name}")
            
            # --- FIX 1: Correct path ---
            # (Your configs are in 'networks/', not 'networks_conditions/')
            profile_path = f"configs/network_conditions/{profile_name}.json"
            
            # Import here to avoid circular dependency
            from .network_emulator import NetworkEmulator 
            
            # Use 'lo' for local testing (requires sudo)
            emulator = NetworkEmulator.from_profile(profile_path, interface="lo")
        
        # --- 2. CREATE ORCHESTRATOR ---
        orch = Orchestrator(cfg["protocol"], cfg)

        # --- (FailureInjector code could go here if you want to use it) ---
        
        # --- 3. GENERATE STREAM ---
        stream = generate_sensor_stream(cfg)
        
        # --- 4. RUN TEST ---
        ok = orch.run_test(stream)

    except KeyboardInterrupt:
        _LOG.warning("Test interrupted by user")
        ok = False
    except Exception as e:
        _LOG.exception("Test failed")
        ok = False
    finally:
        # --- 5. CLEANUP (CRITICAL) ---
        _LOG.info("Cleaning up test...")
        if orch:
            orch.protocol.stop()
        if emulator:
            emulator.clear()
            _LOG.info("Network emulation cleared.")
    
    # --- 6. SAVE REPORT ---
    if ok or (orch and orch.metrics["sent"] > 0):
        timestamp = int(time.time())
        
        # Use a scenario-based name if available
        scenario_name = "default"
        if "_source" in cfg:
            scenario_name = cfg.get('_source', 'unknown').split(':')[-1]
            # remove .json
            scenario_name = scenario_name.replace('.json', '')
            
        out_dir = Path("results") / f"{cfg['protocol']}_{scenario_name}_{timestamp}"
        
        orch.save_report(out_dir)
        _LOG.info("Test completed successfully")
        return True
    else:
        _LOG.error("Test failed - no results saved")
        return False


def run_comparison(protocols: list, scenario_cfg: dict):
    """
    @brief Run comparison of multiple protocols.
    
    @details Runs the ProtocolComparator to execute tests sequentially against 
             a common scenario and generates a comparative report.

    @param protocols List of protocol names (strings) to compare.
    @param scenario_cfg Base configuration dictionary representing the scenario.
    @return None
    """
    from .comparator import ProtocolComparator
    
    _LOG.info(f"Comparing protocols: {', '.join(protocols)}")
    
    # Save scenario as temp file
    temp_scenario = Path("temp_scenario.json")
    temp_scenario.write_text(json.dumps(scenario_cfg, indent=2))
    
    try:
        comparator = ProtocolComparator(str(temp_scenario), protocols)
        comparator.run_comparison()
        
        # Generate report
        timestamp = int(time.time())
        report_file = f"results/comparisons/comparison_{timestamp}.txt"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        comparator.generate_report(report_file)
        
        _LOG.info(f"Comparison complete - report saved to {report_file}")
    finally:
        temp_scenario.unlink(missing_ok=True)


def main():
    """
    @brief Main entry point.
    
    @details Routes execution based on arguments:
             - List operations (scenarios/protocols)
             - Config loading (File vs Scenario)
             - Execution mode (Single Test vs Comparison)
    
    @return None
    """
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle list commands
    if args.list_scenarios:
        list_scenarios()
        return
    
    if args.list_protocols:
        list_protocols()
        return
    
    # Load configuration
    if args.config:
        # Load from file
        try:
            cfg = load_config(args.config)
            cfg["_source"] = args.config
        except Exception as e:
            _LOG.error(f"Failed to load config: {e}")
            sys.exit(1)
    elif args.scenario:
        # Load from scenario
        try:
            cfg = load_scenario(args.scenario)
            cfg["_source"] = f"scenario:{args.scenario}"
            
            # Override protocol if specified
            if args.protocol:
                cfg["protocol"] = args.protocol
        except Exception as e:
            _LOG.error(f"Failed to load scenario: {e}")
            sys.exit(1)
    else:
        _LOG.error("No configuration specified. Use --config or --scenario")
        sys.exit(1)
    
    # Add validation flag
    if args.validate:
        cfg["validate"] = True
    
    # Run comparison or single test
    if args.compare:
        protocols = [p.strip() for p in args.compare.split(",")]
        run_comparison(protocols, cfg)
    else:
        success = run_single_test(cfg)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()