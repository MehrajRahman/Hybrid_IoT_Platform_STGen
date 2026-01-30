#!/usr/bin/env python3
"""
Real Protocol Comparison: MQTT vs CoAP vs PRTP
Uses ACTUAL protocol traffic for benchmarking.

This is for the DCOSS paper comparing IoT protocols.
"""
import sys
sys.path.insert(0, '.')
import time
import logging
import statistics
from typing import Dict, Any, List

logging.basicConfig(level=logging.WARNING)

def test_mqtt(num_messages: int = 100) -> Dict[str, Any]:
    """Test MQTT protocol with real broker."""
    print("\n" + "="*60)
    print("Testing MQTT (Mosquitto)")
    print("="*60)
    
    try:
        from protocols.mqtt.mqtt import Protocol as MQTTProtocol
        
        mqtt = MQTTProtocol({
            'broker_port': 1883,
            'num_clients': 1,
            'topic': 'stgen/benchmark',
        })
        
        mqtt.start_server()
        time.sleep(1)
        mqtt.start_clients(1)
        time.sleep(1)
        
        latencies = []
        sent = 0
        
        print(f"  Sending {num_messages} messages...")
        for i in range(num_messages):
            start = time.perf_counter()
            success, _ = mqtt.send_data('client_0', {'sensor_id': 'temp_0', 'value': f'{20+i%10}.5'})
            end = time.perf_counter()
            if success:
                latencies.append((end - start) * 1000)
                sent += 1
            time.sleep(0.01)  # 10ms between messages
        
        time.sleep(1)
        mqtt.stop()
        
        return {
            'protocol': 'MQTT',
            'sent': sent,
            'latencies': latencies,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        }
    except Exception as e:
        print(f"  MQTT test failed: {e}")
        return {'protocol': 'MQTT', 'error': str(e)}


def test_coap(num_messages: int = 100) -> Dict[str, Any]:
    """Test CoAP protocol."""
    print("\n" + "="*60)
    print("Testing CoAP")
    print("="*60)
    
    try:
        from protocols.coap.coap import Protocol as CoAPProtocol
        
        coap = CoAPProtocol({
            'server_ip': '127.0.0.1',
            'server_port': 5683,
            'num_clients': 1,
        })
        
        coap.start_server()
        time.sleep(1)
        coap.start_clients(1)
        time.sleep(1)
        
        latencies = []
        sent = 0
        
        print(f"  Sending {num_messages} messages...")
        for i in range(num_messages):
            start = time.perf_counter()
            success, _ = coap.send_data('client_0', {'sensor_id': 'temp_0', 'value': f'{20+i%10}.5'})
            end = time.perf_counter()
            if success:
                latencies.append((end - start) * 1000)
                sent += 1
            time.sleep(0.01)
        
        time.sleep(1)
        coap.stop()
        
        return {
            'protocol': 'CoAP',
            'sent': sent,
            'latencies': latencies,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        }
    except Exception as e:
        print(f"  CoAP test failed: {e}")
        return {'protocol': 'CoAP', 'error': str(e)}


def test_prtp(num_messages: int = 100) -> Dict[str, Any]:
    """Test PRTP protocol with real C binaries."""
    print("\n" + "="*60)
    print("Testing PRTP (PRIoTP)")
    print("="*60)
    
    try:
        from protocols.prtp.prtp import Protocol as PRTPProtocol
        import os
        os.system("pkill -9 PRTP 2>/dev/null")
        time.sleep(0.5)
        
        prtp = PRTPProtocol({
            'sensor_port': 5000,
            'client_port': 5001,
            'num_clients': 1,
            'sensors': ['temp'],
        })
        
        prtp.start_server(num_sensors=1)
        time.sleep(1)
        prtp.start_clients(1)
        time.sleep(2)  # Extra time for PRTP subscription
        
        # Check if client is running
        if prtp._clients and prtp._clients[0].process.poll() is not None:
            return {'protocol': 'PRTP', 'error': 'Client crashed'}
        
        print(f"  Sending {num_messages} messages...")
        for i in range(num_messages):
            prtp.send_data('temp_0', {'value': f'{20+i%10}.5 C'})
            time.sleep(0.01)
        
        time.sleep(2)  # Wait for delivery
        prtp.stop()
        
        metrics = prtp.collect_metrics()
        latencies = metrics.get('real_latencies_ms', [])
        
        return {
            'protocol': 'PRTP',
            'sent': metrics.get('messages_sent', 0),
            'received': metrics.get('messages_received', 0),
            'latencies': latencies,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        }
    except Exception as e:
        print(f"  PRTP test failed: {e}")
        import traceback
        traceback.print_exc()
        return {'protocol': 'PRTP', 'error': str(e)}


def print_results(results: List[Dict[str, Any]]):
    """Print comparison table."""
    print("\n" + "="*80)
    print("PROTOCOL COMPARISON RESULTS (Localhost - No Network Conditions)")
    print("="*80)
    print(f"{'Protocol':<10} {'Sent':>8} {'Avg Latency':>12} {'Min':>10} {'Max':>10} {'StdDev':>10}")
    print("-"*80)
    
    for r in results:
        if 'error' in r:
            print(f"{r['protocol']:<10} ERROR: {r['error']}")
        else:
            print(f"{r['protocol']:<10} {r.get('sent', 0):>8} {r.get('avg_latency', 0):>10.2f}ms "
                  f"{r.get('min_latency', 0):>8.2f}ms {r.get('max_latency', 0):>8.2f}ms "
                  f"{r.get('std_latency', 0):>8.2f}ms")
    
    print("="*80)
    print("\nNOTES:")
    print("- MQTT latency = time from publish() call to return (includes TCP ACK)")
    print("- CoAP latency = time from request to response (CON mode)")
    print("- PRTP latency = time from UDP send to client log write (end-to-end)")
    print("-"*80)
    print("On localhost, all protocols perform similarly (~1-10ms).")
    print("PRTP's advantages appear under packet loss conditions.")
    print("="*80)


def main():
    print("="*80)
    print("IoT Protocol Benchmark - REAL Traffic Comparison")
    print("MQTT (TCP) vs CoAP (UDP+CON) vs PRTP (UDP+Q-learning)")
    print("="*80)
    
    num_messages = 50  # Number of messages per protocol
    
    results = []
    
    # Test each protocol
    results.append(test_mqtt(num_messages))
    results.append(test_coap(num_messages))
    results.append(test_prtp(num_messages))
    
    # Print comparison
    print_results(results)


if __name__ == "__main__":
    main()
