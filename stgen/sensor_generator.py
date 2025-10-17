# stgen/sensor_generator.py
"""
Multi-Sensor Traffic Stream Generator
Generates realistic IoT sensor data streams with varied timing patterns.
"""

import random
import time
from typing import Generator, Tuple, Dict, Any


def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict[str, Any], float], None, None]:
    """
    Generate realistic sensor data stream.
    
    Args:
        cfg: Configuration with keys:
            - duration: Test duration in seconds
            - num_clients: Number of sensor clients
            - sensors: List of sensor types
    
    Yields:
        Tuple of (client_id, data_dict, timeout)
        where timeout is inter-packet delay
    """
    dur = cfg.get("duration", 30)
    num = cfg.get("num_clients", 4)
    sensors = cfg.get("sensors", ["temp", "gps", "device", "camera"])
    
    start = time.time()
    seq = 0
    
    # Initialize client states
    states = {}
    for i in range(num):
        cid = f"client_{i}"
        states[cid] = {
            "mean": random.uniform(-30, 50),      # Temperature baseline
            "motion": random.choice([0, 1]),       # Motion state
            "lat": 23.8 + random.uniform(-0.5, 0.5),  # GPS latitude
            "lon": 90.4 + random.uniform(-0.5, 0.5)   # GPS longitude
        }
    
    while time.time() - start < dur:
        for i in range(num):
            cid = f"client_{i}"
            seq += 1
            seq %= 65536  # Wrap at 16-bit boundary
            
            sensor = sensors[i % len(sensors)]
            
            # Generate sensor-specific data and timing
            if sensor == "temp":
                # Temperature: Normal distribution with slow drift
                val = round(random.normalvariate(states[cid]["mean"], 10), 1)
                states[cid]["mean"] += random.uniform(-0.1, 0.1)  # Drift
                data = f"{val} C"
                to = 1.0  # 1 Hz
                
            elif sensor == "device":
                # Binary device state (ON/OFF)
                data = random.choice(["OFF", "ON"])
                to = random.uniform(0.1, 5)  # Irregular
                
            elif sensor == "gps":
                # GPS coordinates with random walk
                states[cid]["lat"] += random.uniform(-0.001, 0.001)
                states[cid]["lon"] += random.uniform(-0.001, 0.001)
                data = f"[{states[cid]['lat']:.6f}, {states[cid]['lon']:.6f}]"
                to = 5.0  # 0.2 Hz
                
            elif sensor == "camera":
                # Motion detection camera (burst on motion)
                if states[cid]["motion"]:
                    data = "MOTION_DETECTED"
                    to = 0.067  # ~15 fps during motion
                    
                    # Random motion end
                    if random.random() > 0.95:
                        states[cid]["motion"] = 0
                else:
                    data = "NO_MOTION"
                    to = random.uniform(1, 10)  # Low rate when idle
                    
                    # Random motion start
                    if random.random() > 0.8:
                        states[cid]["motion"] = 1
            
            elif sensor == "humidity":
                # Humidity sensor (correlated with temp)
                base_hum = 50 + (states[cid]["mean"] - 20) * 0.5
                val = round(random.normalvariate(base_hum, 5), 1)
                data = f"{val}%"
                to = 2.0  # 0.5 Hz
            
            elif sensor == "motion":
                # PIR motion sensor (binary)
                data = random.choice(["MOTION", "STILL"])
                to = random.uniform(0.5, 3)
            
            else:
                data = "UNKNOWN"
                to = 1.0
            
            # Package sensor reading
            payload = {
                "dev_id": f"{sensor}_{i}",
                "ts": time.time(),
                "seq_no": seq,
                "sensor_data": data
            }
            
            yield (cid, payload, to)
            
            # Break if duration exceeded
            if time.time() - start >= dur:
                return