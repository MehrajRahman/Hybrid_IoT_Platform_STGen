#!/usr/bin/env python3
"""
Test script to verify PRTP integration fixes.

This tests:
1. sensor.list is created correctly with matching sensor IDs
2. PRTP_server starts and reads sensor.list
3. PRTP_client subscribes and receives messages
4. Log files are created in the correct directory
5. Latency can be calculated from send/receive times
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

from protocols.prtp.prtp import Protocol as PRTPProtocol

def test_prtp_basic():
    """Test basic PRTP functionality."""
    print("\n" + "=" * 70)
    print("PRTP Integration Fix Test")
    print("=" * 70)
    
    # Configuration
    config = {
        "protocol": "prtp",
        "mode": "active",
        "server_ip": "127.0.0.1",
        "sensor_port": 5000,
        "client_port": 5001,
        "num_clients": 5,  # Test with 5 sensors
        "sensors": ["temp"],  # Use only temp sensors for simplicity
        "duration": 10,
    }
    
    print(f"\nConfiguration:")
    print(f"  - Sensors: {config['num_clients']}")
    print(f"  - Sensor types: {config['sensors']}")
    print(f"  - Duration: {config['duration']}s")
    
    # Initialize protocol
    print("\n[1] Initializing PRTP protocol...")
    prtp = PRTPProtocol(config)
    
    print(f"  ✓ PRTP binary path: {prtp.prtp_path}")
    print(f"  ✓ Log directory: {prtp._log_base}")
    
    try:
        # Start server
        print("\n[2] Starting PRTP_server...")
        prtp.start_server(num_sensors=config['num_clients'])
        time.sleep(2)  # Wait for server to fully start
        
        # Check sensor.list was created
        sensor_list = prtp._log_base / "sensor.list"
        if sensor_list.exists():
            print(f"  ✓ sensor.list created at: {sensor_list}")
            print(f"    Contents:")
            for line in sensor_list.read_text().strip().split('\n'):
                print(f"      - {line}")
        else:
            print(f"  ✗ sensor.list NOT found at: {sensor_list}")
        
        # Start clients
        print("\n[3] Starting PRTP clients...")
        prtp.start_clients(config['num_clients'])
        time.sleep(3)  # Wait for clients to subscribe
        
        print(f"  ✓ Started {len(prtp._sensors)} sensors")
        print(f"  ✓ Started {len(prtp._clients)} clients")
        
        # Check client log directories
        for client in prtp._clients:
            if client.log_dir.exists():
                print(f"  ✓ Client {client.client_id} log dir: {client.log_dir}")
            else:
                print(f"  ✗ Client {client.client_id} log dir NOT found: {client.log_dir}")
        
        # Send some test messages
        print("\n[4] Sending test messages...")
        num_messages = 50
        sent_count = 0
        
        for i in range(num_messages):
            client_id = f"client_{i % config['num_clients']}"
            data = {
                "sensor_data": f"{20 + (i % 10)}.{i % 10} C"
            }
            success, _ = prtp.send_data(client_id, data)
            if success:
                sent_count += 1
            
            time.sleep(0.05)  # 50ms between messages
            
            if (i + 1) % 10 == 0:
                print(f"  Sent {i + 1}/{num_messages} messages...")
        
        print(f"\n  ✓ Sent {sent_count}/{num_messages} messages")
        
        # Wait for messages to be received and logged
        print("\n[5] Waiting for messages to be received...")
        time.sleep(3)
        
        # Stop and collect metrics
        print("\n[6] Stopping PRTP and collecting metrics...")
        prtp.stop()
        
        # Get final metrics
        print("\n[7] Final metrics:")
        metrics = prtp.collect_metrics()
        
        print(f"  - Messages sent: {metrics['messages_sent']}")
        print(f"  - Messages received: {metrics['messages_received']}")
        print(f"  - Packet loss: {metrics['packet_loss_pct']:.2f}%")
        
        if metrics['average_latency_ms'] is not None:
            print(f"  - Avg latency: {metrics['average_latency_ms']:.2f} ms")
            print(f"  - Min latency: {metrics['min_latency_ms']:.2f} ms")
            print(f"  - Max latency: {metrics['max_latency_ms']:.2f} ms")
        else:
            print("  - Latency: No samples collected")
        
        # Check log files
        print("\n[8] Checking log files...")
        for client in prtp._clients:
            if client.log_dir.exists():
                log_files = list(client.log_dir.glob("*.log"))
                print(f"  Client {client.client_id}: {len(log_files)} log files")
                for lf in log_files:
                    size = lf.stat().st_size
                    lines = len(lf.read_text().strip().split('\n')) if size > 0 else 0
                    print(f"    - {lf.name}: {size} bytes, {lines} lines")
        
        # Summary
        print("\n" + "=" * 70)
        if metrics['messages_received'] > 0:
            print("✓ TEST PASSED: PRTP received messages successfully!")
            loss_rate = (metrics['messages_sent'] - metrics['messages_received']) / max(metrics['messages_sent'], 1) * 100
            print(f"  Delivery rate: {100 - loss_rate:.1f}%")
        else:
            print("✗ TEST FAILED: PRTP did not receive any messages")
            print("  Check the logs above for debugging info")
        print("=" * 70)
        
        return metrics['messages_received'] > 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to stop
        try:
            prtp.stop()
        except:
            pass
        
        return False


if __name__ == "__main__":
    success = test_prtp_basic()
    sys.exit(0 if success else 1)
