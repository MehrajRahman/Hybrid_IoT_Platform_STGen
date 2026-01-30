#!/usr/bin/env python3
"""
Direct test of PRTP binaries to verify log collection works.
This bypasses the STGen framework for debugging.
"""
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

PRTP_PATH = Path("/home/mehraj-rahman/Desktop/STGen+PRIoTP/PRTP_development (Copy)/PRTP/application")

def main():
    # Clean up
    os.system("pkill -9 -f PRTP_server 2>/dev/null; pkill -9 -f PRTP_client 2>/dev/null")
    time.sleep(1)
    
    # Clean old logs
    log_dir = PRTP_PATH / "test_direct_log"
    if log_dir.exists():
        import shutil
        shutil.rmtree(log_dir)
    
    print("=" * 50)
    print("PRTP Direct Test")
    print("=" * 50)
    
    # Start server
    print("\n[1] Starting PRTP_server...")
    server = subprocess.Popen(
        [str(PRTP_PATH / "PRTP_server"),
         "-i127.0.0.1", "-p5000", "-s5001",
         "-l./sensor.list", "-c./clients.conf",
         "-q./q_agent_trained.csv"],
        cwd=str(PRTP_PATH),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid  # Server can use setsid
    )
    time.sleep(1)
    print(f"    Server PID: {server.pid}")
    
    # Start client WITHOUT setsid - this is critical!
    print("\n[2] Starting PRTP_client...")
    client = subprocess.Popen(
        [str(PRTP_PATH / "PRTP_client"),
         "-ltest_direct_log",  # Relative to CWD
         "-s127.0.0.1", "-p5001", "-A"],
        cwd=str(PRTP_PATH),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # NO preexec_fn=os.setsid - this is the key fix!
    )
    time.sleep(2)
    print(f"    Client PID: {client.pid}")
    
    # Send test messages
    print("\n[3] Sending test messages...")
    send_times = {}
    for i in range(10):
        seq = i + 1
        send_time = time.time()
        msg = f"{{'dev_id': 'temp_0', 'ts': '{send_time}', 'seq_no': '{seq}', 'data_size': '6', 'sensor_data': '25.{i} C'}}"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg.encode(), ("127.0.0.1", 5000))
        sock.close()
        
        send_times[seq] = send_time
        print(f"    Sent message {seq}")
        time.sleep(0.2)
    
    # Wait for delivery
    print("\n[4] Waiting for message delivery...")
    time.sleep(2)
    
    # Check log before stopping
    print("\n[5] Log directory BEFORE stopping client:")
    if log_dir.exists():
        for f in log_dir.glob("*.log"):
            size = f.stat().st_size
            lines = f.read_text().count('\n')
            print(f"    {f.name}: {size} bytes, {lines} lines")
    else:
        print("    Log dir does not exist yet!")
    
    # Stop client with SIGINT (graceful shutdown to flush logs)
    print("\n[6] Stopping client with SIGINT...")
    os.kill(client.pid, signal.SIGINT)
    time.sleep(1)
    
    # Check log after stopping
    print("\n[7] Log directory AFTER stopping client:")
    if log_dir.exists():
        for f in log_dir.glob("*.log"):
            size = f.stat().st_size
            content = f.read_text()
            lines = content.strip().split('\n') if content.strip() else []
            print(f"    {f.name}: {size} bytes, {len(lines)} lines")
            
            # Parse and show latency
            if lines:
                print(f"    Sample entries:")
                for line in lines[:5]:
                    parts = line.split(None, 2)
                    if len(parts) >= 2:
                        recv_time = float(parts[0])
                        seq = int(parts[1])
                        if seq in send_times:
                            latency_ms = (recv_time - send_times[seq]) * 1000
                            print(f"      seq={seq}: latency={latency_ms:.2f}ms")
    else:
        print("    ERROR: Log dir still does not exist!")
    
    # Cleanup
    print("\n[8] Cleanup...")
    try:
        os.killpg(os.getpgid(server.pid), signal.SIGKILL)
    except:
        pass
    print("    Done!")

if __name__ == "__main__":
    main()
