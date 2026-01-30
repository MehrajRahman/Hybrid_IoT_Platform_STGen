#!/usr/bin/env python3
"""
Full PRTP integration test with real latency measurement.
"""
import sys
sys.path.insert(0, '.')
from protocols.prtp.prtp import Protocol
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

def main():
    print("=" * 60)
    print("PRTP Full Integration Test - REAL Latency Measurement")
    print("=" * 60)
    
    # Create PRTP protocol with 1 sensor/client pair
    # Note: Multiple PRTP_client instances may cause segfaults
    config = {
        'sensor_port': 5000,
        'client_port': 5001,
        'num_clients': 1,
        'sensors': ['temp'],
    }
    
    prtp = Protocol(config)
    
    # Start server
    print("\n[1] Starting PRTP server...")
    prtp.start_server(num_sensors=1)
    time.sleep(1)
    
    # Start client
    print("\n[2] Starting PRTP client...")
    prtp.start_clients(1)
    time.sleep(3)  # Extra time for subscription
    
    # Send messages (only to temp_0 since we have 1 sensor)
    print("\n[3] Sending 20 messages...")
    for i in range(20):
        prtp.send_data('temp_0', {'value': f'{20+i}.5 C'})
        time.sleep(0.1)
    
    # Wait for delivery
    print("\n[4] Waiting for message delivery...")
    time.sleep(3)
    
    # Stop and collect
    print("\n[5] Stopping and collecting metrics...")
    prtp.stop()
    time.sleep(1)
    
    # Get results
    metrics = prtp.collect_metrics()
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Messages sent:     {metrics.get('messages_sent', 0)}")
    print(f"Messages received: {metrics.get('messages_received', 0)}")
    print(f"Packet loss:       {metrics.get('packet_loss_pct', 0):.1f}%")
    
    latencies = metrics.get('real_latencies_ms', [])
    print(f"Latency samples:   {len(latencies)}")
    
    if latencies:
        print(f"Average latency:   {metrics.get('average_latency_ms', 0):.2f} ms")
        print(f"Min latency:       {metrics.get('min_latency_ms', 0):.2f} ms")
        print(f"Max latency:       {metrics.get('max_latency_ms', 0):.2f} ms")
        print(f"Std deviation:     {metrics.get('std_latency_ms', 0):.2f} ms")
        print(f"\nFirst 10 latencies (ms): {[round(l, 2) for l in latencies[:10]]}")
    else:
        print("\n** NO LATENCY DATA - Client logs may be empty **")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
