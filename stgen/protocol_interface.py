# stgen/protocol_interface.py
"""
@file protocol_interface.py
@brief Protocol Interface Contract for STGen
@details Defines the abstract base class that all protocol implementations must inherit from.
         This interface enforces consistency across different IoT protocols (e.g., CoAP, MQTT),
         allowing the orchestrator to manage them uniformly regardless of their underlying 
         transport mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class ProtocolInterface(ABC):
    """
    @brief Base class for all protocol implementations in STGen.
    
    @details Protocols can operate in two modes:
             - 'active': STGen orchestrator explicitly calls send_data() for each packet.
             - 'passive': Protocol binaries/scripts run autonomously (e.g., shell scripts), 
                          while STGen monitors their process state and logs.
    """
    
    def __init__(self, cfg: Dict[str, Any]):
        """
        @brief Initialize protocol with configuration.
        
        @param cfg Configuration dictionary containing standard keys:
                   - mode: 'active' or 'passive'
                   - server_ip: Server address
                   - server_port: Server port
                   - num_clients: Number of client instances
                   - duration: Test duration in seconds
                   - [protocol-specific params]
        """
        self.cfg = cfg
        self.mode = cfg.get("mode", "active")
        self._alive = True
    
    @abstractmethod
    def start_server(self) -> None:
        """
        @brief Start the server process/thread.
        
        @details Should bind to cfg['server_ip:port'] and run in the background.
                 This method must return immediately (non-blocking) to allow the 
                 orchestrator to proceed.
        
        @return None
        """
        pass
    
    @abstractmethod
    def start_clients(self, num: int) -> None:
        """
        @brief Launch N client processes/threads.
        
        @details Clients should establish connections to the server but typically 
                 should not start streaming data until commanded (in Active mode).
        
        @param num Number of client instances to start.
        @return None
        """
        pass
    
    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """
        @brief Send sensor data from a specific client (ACTIVE MODE ONLY).
        
        @param client_id Identifier for the client instance sending the data.
        @param data Sensor data dictionary with standard keys:
                    - dev_id: Device identifier
                    - ts: Timestamp
                    - seq_no: Sequence number
                    - sensor_data: Actual sensor reading payload
        
        @return Tuple[bool, float] A tuple containing:
                - success (bool): True if the transmission was successful.
                - timestamp (float): The timestamp of receipt at the server (for latency calculation).
        
        @note For passive protocols, this can raise NotImplementedError or return 
              (True, 0.0) as placeholder values since STGen doesn't drive the traffic.
        
        @exception NotImplementedError If not implemented by the specific protocol subclass.
        """
        raise NotImplementedError("Use passive mode or override send_data")
    
    @abstractmethod
    def stop(self) -> None:
        """
        @brief Gracefully shutdown all clients and server.
        
        @details Must ensure all spawned processes, threads, or sockets are 
                 terminated/closed to prevent resource leaks.
        
        @return None
        """
        pass
    
    def is_alive(self) -> bool:
        """
        @brief Check if protocol processes are still running.
        
        @return bool True if protocol is operational, False otherwise.
        """
        return self._alive
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        @brief Optional: Return protocol-specific metrics.
        
        @details Subclasses can override this to provide metrics unique to their 
                 transport layer (e.g., retransmission counts for TCP-based protocols).
        
        @return Dict[str, Any] Dictionary with protocol-specific performance data.
        """
        return {}