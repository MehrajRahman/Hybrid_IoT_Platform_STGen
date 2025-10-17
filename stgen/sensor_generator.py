# # stgen/sensor_generator.py
# """
# Multi-Sensor Traffic Stream Generator
# Generates realistic IoT sensor data streams with varied timing patterns.
# """

# import random
# import time
# from typing import Generator, Tuple, Dict, Any


# def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict[str, Any], float], None, None]:
#     """
#     Generate realistic sensor data stream.
    
#     Args:
#         cfg: Configuration with keys:
#             - duration: Test duration in seconds
#             - num_clients: Number of sensor clients
#             - sensors: List of sensor types
    
#     Yields:
#         Tuple of (client_id, data_dict, timeout)
#         where timeout is inter-packet delay
#     """
#     dur = cfg.get("duration", 30)
#     num = cfg.get("num_clients", 4)
#     sensors = cfg.get("sensors", ["temp", "gps", "device", "camera"])
    
#     start = time.time()
#     seq = 0
    
#     # Initialize client states
#     states = {}
#     for i in range(num):
#         cid = f"client_{i}"
#         states[cid] = {
#             "mean": random.uniform(-30, 50),      # Temperature baseline
#             "motion": random.choice([0, 1]),       # Motion state
#             "lat": 23.8 + random.uniform(-0.5, 0.5),  # GPS latitude
#             "lon": 90.4 + random.uniform(-0.5, 0.5)   # GPS longitude
#         }
    
#     while time.time() - start < dur:
#         for i in range(num):
#             cid = f"client_{i}"
#             seq += 1
#             seq %= 65536  # Wrap at 16-bit boundary
            
#             sensor = sensors[i % len(sensors)]
            
#             # Generate sensor-specific data and timing
#             if sensor == "temp":
#                 # Temperature: Normal distribution with slow drift
#                 val = round(random.normalvariate(states[cid]["mean"], 10), 1)
#                 states[cid]["mean"] += random.uniform(-0.1, 0.1)  # Drift
#                 data = f"{val} C"
#                 to = 1.0  # 1 Hz
                
#             elif sensor == "device":
#                 # Binary device state (ON/OFF)
#                 data = random.choice(["OFF", "ON"])
#                 to = random.uniform(0.1, 5)  # Irregular
                
#             elif sensor == "gps":
#                 # GPS coordinates with random walk
#                 states[cid]["lat"] += random.uniform(-0.001, 0.001)
#                 states[cid]["lon"] += random.uniform(-0.001, 0.001)
#                 data = f"[{states[cid]['lat']:.6f}, {states[cid]['lon']:.6f}]"
#                 to = 5.0  # 0.2 Hz
                
#             elif sensor == "camera":
#                 # Motion detection camera (burst on motion)
#                 if states[cid]["motion"]:
#                     data = "MOTION_DETECTED"
#                     to = 0.067  # ~15 fps during motion
                    
#                     # Random motion end
#                     if random.random() > 0.95:
#                         states[cid]["motion"] = 0
#                 else:
#                     data = "NO_MOTION"
#                     to = random.uniform(1, 10)  # Low rate when idle
                    
#                     # Random motion start
#                     if random.random() > 0.8:
#                         states[cid]["motion"] = 1
            
#             elif sensor == "humidity":
#                 # Humidity sensor (correlated with temp)
#                 base_hum = 50 + (states[cid]["mean"] - 20) * 0.5
#                 val = round(random.normalvariate(base_hum, 5), 1)
#                 data = f"{val}%"
#                 to = 2.0  # 0.5 Hz
            
#             elif sensor == "motion":
#                 # PIR motion sensor (binary)
#                 data = random.choice(["MOTION", "STILL"])
#                 to = random.uniform(0.5, 3)
            
#             else:
#                 data = "UNKNOWN"
#                 to = 1.0
            
#             # Package sensor reading
#             payload = {
#                 "dev_id": f"{sensor}_{i}",
#                 "ts": time.time(),
#                 "seq_no": seq,
#                 "sensor_data": data
#             }
            
#             yield (cid, payload, to)
            
#             # Break if duration exceeded
#             if time.time() - start >= dur:
#                 return



# stgen/sensor_generator.py
"""
Sensor data generator for IoT testing.
Generates realistic sensor readings based on sensor type.
"""

import random
import time
from typing import Dict, Any, Generator, Tuple


def generate_sensor_value(sensor_type: str) -> Dict[str, Any]:
    """
    Generate realistic sensor data based on type.
    
    Args:
        sensor_type: Type of sensor (temp, humidity, motion, etc.)
    
    Returns:
        Dictionary with sensor-specific data
    """
    if sensor_type == "temp" or sensor_type == "temperature":
        return {
            "value": round(random.uniform(15.0, 35.0), 2),
            "unit": "C"
        }
    
    elif sensor_type == "humidity":
        return {
            "value": round(random.uniform(30.0, 80.0), 2),
            "unit": "%"
        }
    
    elif sensor_type == "motion" or sensor_type == "pir":
        return {
            "detected": random.choice([True, False]),
            "confidence": round(random.uniform(0.5, 1.0), 2)
        }
    
    elif sensor_type == "light" or sensor_type == "lux":
        return {
            "value": round(random.uniform(0, 1000), 2),
            "unit": "lux"
        }
    
    elif sensor_type == "pressure":
        return {
            "value": round(random.uniform(980, 1040), 2),
            "unit": "hPa"
        }
    
    elif sensor_type == "gps" or sensor_type == "location":
        return {
            "latitude": round(random.uniform(-90, 90), 6),
            "longitude": round(random.uniform(-180, 180), 6),
            "altitude": round(random.uniform(0, 500), 2)
        }
    
    elif sensor_type == "accelerometer" or sensor_type == "accel":
        return {
            "x": round(random.uniform(-10, 10), 3),
            "y": round(random.uniform(-10, 10), 3),
            "z": round(random.uniform(-10, 10), 3),
            "unit": "m/s²"
        }
    
    elif sensor_type == "gyroscope" or sensor_type == "gyro":
        return {
            "x": round(random.uniform(-250, 250), 2),
            "y": round(random.uniform(-250, 250), 2),
            "z": round(random.uniform(-250, 250), 2),
            "unit": "°/s"
        }
    
    elif sensor_type == "camera" or sensor_type == "image":
        return {
            "resolution": "1920x1080",
            "format": "JPEG",
            "size_kb": random.randint(50, 500)
        }
    
    elif sensor_type == "sound" or sensor_type == "audio":
        return {
            "level": round(random.uniform(30, 90), 2),
            "unit": "dB"
        }
    
    elif sensor_type == "vibration":
        return {
            "frequency": round(random.uniform(10, 100), 2),
            "amplitude": round(random.uniform(0, 10), 2),
            "unit": "Hz"
        }
    
    elif sensor_type == "co2":
        return {
            "value": round(random.uniform(400, 1000), 2),
            "unit": "ppm"
        }
    
    elif sensor_type == "voltage":
        return {
            "value": round(random.uniform(3.0, 5.0), 2),
            "unit": "V"
        }
    
    else:
        # Generic fallback for unknown sensor types
        return {
            "value": round(random.uniform(0, 100), 2),
            "type": sensor_type,
            "unit": "generic"
        }


def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
    """
    Generate a stream of sensor readings.
    
    Args:
        cfg: Configuration dictionary with:
            - num_clients: Number of sensor devices
            - duration: Test duration in seconds
            - sensors: List of sensor types
    
    Yields:
        Tuple of (client_id, data_dict, sleep_interval)
    """
    num_clients = cfg.get("num_clients", 4)
    duration = cfg.get("duration", 30)
    sensor_types = cfg.get("sensors", ["temp", "humidity", "motion"])
    
    # Ensure sensor_types is a list
    if isinstance(sensor_types, str):
        sensor_types = [sensor_types]
    
    # Calculate rate
    msgs_per_sec = cfg.get("rate", 1.0)  # messages per second per client
    interval = 1.0 / msgs_per_sec if msgs_per_sec > 0 else 1.0
    
    start_time = time.time()
    seq_no = 0
    
    # Generate device assignments
    devices = []
    for i in range(num_clients):
        sensor_type = sensor_types[i % len(sensor_types)]
        devices.append({
            "id": i,
            "type": sensor_type,
            "dev_id": f"{sensor_type}_{i}"
        })
    
    # Generate data stream
    while (time.time() - start_time) < duration:
        for device in devices:
            seq_no += 1
            
            # Generate sensor reading
            sensor_data = generate_sensor_value(device["type"])
            
            # Create data packet
            data = {
                "dev_id": device["dev_id"],
                "ts": time.time(),
                "seq_no": seq_no,
                "sensor_data": sensor_data
            }
            
            client_id = f"client_{device['id']}"
            
            yield (client_id, data, interval)
    
    # Final log
    elapsed = time.time() - start_time
    print(f"\nSensor stream complete: {seq_no} messages in {elapsed:.1f}s")


def generate_burst_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
    """
    Generate bursty sensor traffic (for stress testing).
    Alternates between high and low activity periods.
    """
    num_clients = cfg.get("num_clients", 4)
    duration = cfg.get("duration", 30)
    sensor_types = cfg.get("sensors", ["temp", "humidity"])
    
    burst_rate = cfg.get("burst_rate", 10)  # msgs/sec during burst
    idle_rate = cfg.get("idle_rate", 0.1)   # msgs/sec during idle
    burst_duration = cfg.get("burst_duration", 5)  # seconds
    idle_duration = cfg.get("idle_duration", 10)   # seconds
    
    start_time = time.time()
    seq_no = 0
    in_burst = True
    phase_start = start_time
    
    devices = []
    for i in range(num_clients):
        sensor_type = sensor_types[i % len(sensor_types)]
        devices.append({
            "id": i,
            "type": sensor_type,
            "dev_id": f"{sensor_type}_{i}"
        })
    
    while (time.time() - start_time) < duration:
        # Switch phases
        phase_elapsed = time.time() - phase_start
        if in_burst and phase_elapsed > burst_duration:
            in_burst = False
            phase_start = time.time()
        elif not in_burst and phase_elapsed > idle_duration:
            in_burst = True
            phase_start = time.time()
        
        # Set rate based on phase
        rate = burst_rate if in_burst else idle_rate
        interval = 1.0 / (rate * num_clients)
        
        for device in devices:
            seq_no += 1
            sensor_data = generate_sensor_value(device["type"])
            
            data = {
                "dev_id": device["dev_id"],
                "ts": time.time(),
                "seq_no": seq_no,
                "sensor_data": sensor_data
            }
            
            client_id = f"client_{device['id']}"
            yield (client_id, data, interval)


# For backward compatibility
def parse_sensor_types(sensor_str: str) -> list:
    """
    Parse sensor type string into list.
    Supports both simple format ("temp,humidity") and distribution format ("temp:40,humidity:30").
    
    Args:
        sensor_str: Comma-separated sensor types
    
    Returns:
        List of sensor type names
    """
    if not sensor_str:
        return ["temp", "humidity", "motion"]
    
    sensors = []
    for item in sensor_str.split(","):
        # Handle distribution format (temp:40)
        if ":" in item:
            sensor_type = item.split(":")[0].strip()
        else:
            sensor_type = item.strip()
        
        if sensor_type and sensor_type not in sensors:
            sensors.append(sensor_type)
    
    return sensors