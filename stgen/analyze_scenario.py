"""
@file analyze_scenario.py
@brief Smart Agriculture Case Study Analysis Script
@details AUTOMATED ANALYSIS SCRIPT (Section 5.3)
         This script executes the analytic component of the Smart Agriculture case study.
         It aggregates results from previous STGen executions, applies the energy consumption model,
         and generates a comparative report on battery life, latency, and reliability to
         recommend the optimal protocol.
"""

import json
import sys
import logging
from pathlib import Path

# Add stgen to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from energy_model import EnergyModel
except ImportError:
    print("Error: 'energy_model.py' not found in the script's directory.")
    sys.exit(1)

# --- Configuration ---

## @brief Directory containing STGen test results
RESULTS_DIR = Path("../results")

## @brief Path to the specific scenario configuration file used for analysis
SCENARIO_FILE = Path("../configs/scenarios/smart_agriculture.json")

## @brief List of protocol names to include in the comparison
PROTOCOLS_TO_COMPARE = ["mqtt", "coap", "my_udp"] 

# ---------------------

## @brief Configure basic logging to stdout
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger()


def find_latest_result(protocol: str) -> Path | None:
    """
    @brief Finds the latest 'summary.json' for a given protocol.
    
    @details Scans the `RESULTS_DIR` for folders matching the pattern `{protocol}_*`.
             It sorts them by modification time and selects the most recent one.
             
    @note This assumes the latest run for a protocol corresponds to the scenario 
          being analyzed. For best results, clean the 'results' directory before 
          running your case study.
    
    @param protocol The name of the protocol to search for (e.g., 'mqtt').
    @return Path | None Path to the 'summary.json' file if found, else None.
    """
    search_pattern = f"{protocol}_*"
    all_dirs = list(RESULTS_DIR.glob(search_pattern))
    
    if not all_dirs:
        log.warning(f"No result directories found for protocol '{protocol}'")
        return None

    all_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    latest_dir = all_dirs[0]
    summary_file = latest_dir / "summary.json"
    
    if summary_file.exists():
        return summary_file
    else:
        log.warning(f"Found dir {latest_dir} but no summary.json inside.")
        return None


def main():
    """
    @brief Runs the full case study analysis.
    
    @details Performs the following workflow:
             1. Loads the Smart Agriculture scenario configuration.
             2. Initializes the EnergyModel.
             3. Iterates through specified protocols (MQTT, CoAP, UDP).
             4. Retrieves the latest simulation metrics (packet loss, latency) from disk.
             5. Calculates estimated battery life based on scenario traffic patterns.
             6. Prints a ranked comparison (Section 5.3) and a final recommendation (Section 5.4).
             
    @return None
    """
    log.info("--- Running Smart Agriculture Case Study Analysis ---")
    log.info(f"Loading scenario: {SCENARIO_FILE}")
    
    try:
        scenario_config = json.loads(SCENARIO_FILE.read_text())
    except FileNotFoundError:
        log.error(f"FATAL: Scenario file not found: {SCENARIO_FILE}")
        return
    except json.JSONDecodeError as e:
        log.error(f"FATAL: Invalid JSON in {SCENARIO_FILE}: {e}")
        return

    traffic_pattern = scenario_config.get("traffic_pattern")
    duration = scenario_config.get("duration")

    if not traffic_pattern or not duration:
        log.error("FATAL: Scenario file is missing 'traffic_pattern' or 'duration'.")
        return

    model = EnergyModel()
    log.info(f"Battery: {model.BATTERY_MAH} mAh @ {model.VOLTAGE}V")
    log.info("---")

    analysis_results = []

    for proto in PROTOCOLS_TO_COMPARE:
        log.info(f"Analyzing protocol: {proto}...")
        
        summary_file = find_latest_result(proto)
        
        if not summary_file:
            log.warning(f"  Could not find latest result for {proto}. Skipping.\n")
            continue
        
        log.info(f"  Using result file: {summary_file}")
        sim_results = json.loads(summary_file.read_text())
        
        life_days = model.estimate_battery_life(
            traffic_pattern=traffic_pattern,
            sim_results=sim_results,
            duration_s=duration
        )
        
        analysis_results.append({
            "protocol": proto,
            "loss_pct": sim_results.get("loss", 0) * 100,
            "latency_p95": sim_results.get("lat_p95_ms", 0),
            "life_days": life_days,
            "life_months": life_days / 30.4
        })

    if not analysis_results:
        log.error("No results found for any protocol. Aborting.")
        return

    log.info("\n" + "="*55)
    log.info("--- Case Study Results (Section 5.3) ---")
    log.info("="*55)
    
    # Sort by battery life, descending
    analysis_results.sort(key=lambda x: x["life_days"], reverse=True)
    
    for res in analysis_results:
        log.info(f"Protocol: {res['protocol'].upper()}")
        log.info(f"  Packet Loss:   {res['loss_pct']:.2f}%")
        log.info(f"  P95 Latency:   {res['latency_p95']:.2f} ms")
        log.info(f"  Est. Lifetime: {res['life_days']:.1f} days (~{res['life_months']:.1f} months)")
        log.info("---")

    winner = analysis_results[0]
    log.info("\n" + "="*55)
    log.info(f"--- Decision Analysis (Section 5.4) ---")
    log.info("="*55)
    log.info(f" Recommendation: {winner['protocol'].upper()}")
    log.info(f"   Provides the longest battery life ({winner['life_months']:.1f} months) ")
    log.info(f"   under the specified congested network conditions.")


    log.info("\n" + "="*55)
    log.info("--- Real-World Deployment Considerations (Section 5.5) ---")
    log.info("="*55)
    log.info("(!) This model is a *simulation* and has limitations:")
    log.info(" 1. Network Model: Uses 'tc' for emulation, which abstracts real RF effects.")
    log.info(" 2. Power Model: Uses *static* values for TX/RX power. Real-world draw varies.")
    log.info(" 3. Protocol Overhead: Model does not account for protocol-specific re-transmissions,")
    log.info("    which would consume additional energy for protocols like CoAP (CON) or MQTT (QoS 1).")
    log.info("\nRECOMMENDATION: Use these results to select a protocol for *physical validation*.")

if __name__ == "__main__":
    main()