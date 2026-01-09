# stgen/scale_test.py
"""
@file scale_test.py
@brief Automated scalability testing module.
@details Runs a specific protocol against a scenario with increasing load (client counts)
         to determine performance bottlenecks and scalability limits.
"""


def run_scale_test(protocol: str, client_counts: List[int], scenario: str):
    """
    @brief Test protocol with increasing client counts.
    
    @details Loops through a list of client counts (e.g., [10, 50, 100]). For each count:
             1. Loads the base scenario configuration.
             2. Overrides the protocol and number of clients.
             3. Executes the test run.
             4. Collects the results.
             Finally, it triggers a plotting function to visualize the scaling behavior.

    @param protocol The name of the protocol to test (e.g., 'mqtt').
    @param client_counts A list of integers representing the load steps (e.g., [1, 10, 100]).
    @param scenario The name/path of the base scenario to use.
    @return None
    """
    results = {}

    for num_clients in client_counts:
        _LOG.info(f"Testing with {num_clients} clients...")
        cfg = load_scenario(scenario)
        cfg["protocol"] = protocol
        cfg["num_clients"] = num_clients

        # Run test
        result = run_test(cfg)
        results[num_clients] = result

    # Generate scaling graph
    plot_scaling_results(results)
