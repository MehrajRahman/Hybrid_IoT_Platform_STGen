# # """
# # CoAP protocol plugin for STGen – active mode.
# # Runs aiocoap in a separate thread to avoid event-loop clashes.
# # """

# # import sys
# # import asyncio
# # import json
# # import logging
# # import time
# # import threading
# # from pathlib import Path
# # from typing import Any, Dict, List, Tuple

# # try:
# #     from aiocoap import Context, Message, Code
# # except ImportError as exc:
# #     raise ImportError(
# #         "aiocoap not installed – run:  pip install aiocoap[all]==0.4.7"
# #     ) from exc



# # # ensure stgen package is discoverable when run standalone
# # sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# # from stgen.protocol_interface import ProtocolInterface

# # _LOG = logging.getLogger("coap")


# # # --------------------------------------------------------------------------- #
# # class Protocol(ProtocolInterface):
# #     """CoAP plug-in that satisfies STGen ProtocolInterface."""

# #     def __init__(self, cfg: Dict[str, Any]):
# #         super().__init__(cfg)
# #         self._ctx: Context | None = None
# #         self._thread: threading.Thread | None = None
# #         self._loop: asyncio.AbstractEventLoop | None = None
# #         self._lat: List[float] = []  # store latencies
# #         self._alive: bool = True

# #     # ---------- life-cycle -------------------------------------------------- #
# #     def start_server(self) -> None:
# #         """Start aiocoap server in a dedicated thread."""
# #         self._thread = threading.Thread(target=self._run_server, daemon=True)
# #         self._thread.start()
# #         time.sleep(0.5)  # give the socket time to bind
# #         _LOG.info("CoAP server thread started")

# #     def start_clients(self, num: int) -> None:
# #         _LOG.info("CoAP: %d logical clients (implicit)", num)

# #     def stop(self) -> None:
# #         """Stop server and close event loop."""
# #         self._alive = False
# #         if self._loop and self._ctx:
# #             fut = asyncio.run_coroutine_threadsafe(self._ctx.shutdown(), self._loop)
# #             try:
# #                 fut.result(2)
# #             except Exception as e:
# #                 _LOG.warning("shutdown: %s", e)
# #         if self._thread and self._thread.is_alive():
# #             self._thread.join(timeout=2)
# #         _LOG.info("CoAP server stopped")

# #     # ---------- active-mode send ------------------------------------------- #
# #     def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
# #         """Thread-safe CoAP PUT + RTT measurement."""
# #         if not self._loop or not self._ctx:
# #             _LOG.error("CoAP context not ready")
# #             return False, 0.0
# #         future = asyncio.run_coroutine_threadsafe(self._send_async(data), self._loop)
# #         return future.result()

# #     # ------------------------------------------------------------------ #
# #     # ---------------- internal async ---------------------------------- #
# #     def _run_server(self) -> None:
# #         """Run aiocoap event loop forever (in separate thread)."""
# #         asyncio.set_event_loop(asyncio.new_event_loop())
# #         self._loop = asyncio.get_event_loop()
# #         try:
# #             self._ctx = self._loop.run_until_complete(
# #                 Context.create_server_context(
# #                     self._resource,
# #                     bind=(self.cfg["server_ip"], self.cfg["server_port"]),
# #                 )
# #             )
# #             _LOG.info(
# #                 "CoAP server listening on %s:%s",
# #                 self.cfg["server_ip"],
# #                 self.cfg["server_port"],
# #             )
# #             self._loop.run_forever()
# #         finally:
# #             if self._ctx:
# #                 self._loop.run_until_complete(self._ctx.shutdown())

# #     async def _resource(self, request):
# #         """Dummy resource that always replies with 2.04 Changed."""
# #         return Message(code=Code.CHANGED, payload=b"OK")

# #     async def _send_async(self, data: Dict) -> Tuple[bool, float]:
# #         """Perform a CoAP PUT request and measure RTT."""
# #         uri = f'coap://{self.cfg["server_ip"]}:{self.cfg["server_port"]}/data'
# #         t0 = time.perf_counter()
# #         try:
# #             req = Message(
# #                 code=Code.PUT,
# #                 uri=uri,
# #                 payload=json.dumps(data).encode(),
# #                 content_format=0,  # text/plain
# #             )
# #             resp = await self._ctx.request(req).response
# #             latency_ms = (time.perf_counter() - t0) * 1000
# #             self._lat.append(latency_ms)
# #             return True, time.perf_counter()
# #         except Exception as e:
# #             _LOG.warning("CoAP PUT failed: %s", e)
# #             return False, 0.0


# # # Ensure the orchestrator can find the Protocol symbol
# # Protocol = Protocol


# """
# CoAP protocol plugin for STGen – active mode.
# Runs aiocoap in a separate thread to avoid event-loop clashes.
# """

# import sys
# import asyncio
# import json
# import logging
# import time
# import threading
# from pathlib import Path
# from typing import Any, Dict, List, Tuple

# try:
#     from aiocoap import Context, Message, Code, resource
# except ImportError as exc:
#     raise ImportError(
#         "aiocoap not installed – run:  pip install aiocoap[all]==0.4.7"
#     ) from exc

# # ensure stgen package is discoverable when run standalone
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# from stgen.protocol_interface import ProtocolInterface

# _LOG = logging.getLogger("coap")


# # --------------------------------------------------------------------------- #
# class SimpleResource(resource.Resource):
#     """A basic CoAP resource that handles PUT requests."""

#     async def render_put(self, request):
#         _LOG.debug("Received PUT with payload: %s", request.payload.decode())
#         return Message(code=Code.CHANGED, payload=b"OK")


# # --------------------------------------------------------------------------- #
# class Protocol(ProtocolInterface):
#     """CoAP plug-in that satisfies STGen ProtocolInterface."""

#     def __init__(self, cfg: Dict[str, Any]):
#         super().__init__(cfg)
#         self._ctx: Context | None = None
#         self._thread: threading.Thread | None = None
#         self._loop: asyncio.AbstractEventLoop | None = None
#         self._lat: List[float] = []  # store latencies
#         self._alive: bool = True

#     # ---------- life-cycle -------------------------------------------------- #
#     def start_server(self) -> None:
#         """Start aiocoap server in a dedicated thread."""
#         self._thread = threading.Thread(target=self._run_server, daemon=True)
#         self._thread.start()
#         time.sleep(0.5)  # give the socket time to bind
#         _LOG.info("CoAP server thread started")

#     def start_clients(self, num: int) -> None:
#         _LOG.info("CoAP: %d logical clients (implicit)", num)

#     def stop(self) -> None:
#         """Stop server and close event loop."""
#         self._alive = False
#         if self._loop and self._ctx:
#             fut = asyncio.run_coroutine_threadsafe(self._ctx.shutdown(), self._loop)
#             try:
#                 fut.result(2)
#             except Exception as e:
#                 _LOG.warning("shutdown: %s", e)
#         if self._thread and self._thread.is_alive():
#             self._thread.join(timeout=2)
#         _LOG.info("CoAP server stopped")

#     # ---------- active-mode send ------------------------------------------- #
#     def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
#         """Thread-safe CoAP PUT + RTT measurement."""
#         if not self._loop or not self._ctx:
#             _LOG.error("CoAP context not ready")
#             return False, 0.0
#         future = asyncio.run_coroutine_threadsafe(self._send_async(data), self._loop)
#         return future.result()

#     # ---------- internal async --------------------------------------------- #
#     # def _build_site(self) -> resource.Site:
#     #     """Build a simple CoAP resource tree."""
#     #     root = resource.Site()
#     #     root.add_resource(['data'], SimpleResource())
#     #     return root
#     def _build_site(self):
#         root = resource.Site()

#         class RootResource(resource.Resource):
#             async def render_put(self, request):
#                 return Message(code=Code.CHANGED, payload=b"OK")

#         # Handle both '/' and '/data' so clients always get a reply
#         root.add_resource([], RootResource())        # ← root path
#         root.add_resource(['data'], RootResource())  # ← /data path
#         return root


#     def _run_server(self) -> None:
#         """Run aiocoap event loop forever (in separate thread)."""
#         asyncio.set_event_loop(asyncio.new_event_loop())
#         self._loop = asyncio.get_event_loop()
#         try:
#             self._ctx = self._loop.run_until_complete(
#                 Context.create_server_context(
#                     self._build_site(),
#                     bind=(self.cfg["server_ip"], self.cfg["server_port"]),
#                 )
#             )
#             _LOG.info(
#                 "CoAP server listening on %s:%s",
#                 self.cfg["server_ip"],
#                 self.cfg["server_port"],
#             )
#             self._loop.run_forever()
#         finally:
#             if self._ctx:
#                 self._loop.run_until_complete(self._ctx.shutdown())

#     async def _send_async(self, data: Dict) -> Tuple[bool, float]:
#         """Perform a CoAP PUT request and measure RTT."""
#         uri = f'coap://{self.cfg["server_ip"]}:{self.cfg["server_port"]}/data'
#         t0 = time.perf_counter()
#         try:
#             req = Message(
#                 code=Code.PUT,
#                 uri=uri,
#                 payload=json.dumps(data).encode(),
#                 content_format=0,
#             )
#             resp = await self._ctx.request(req).response
#             latency_ms = (time.perf_counter() - t0) * 1000
#             self._lat.append(latency_ms)
#             _LOG.debug("CoAP PUT response: %s, RTT=%.2f ms", resp.code, latency_ms)
#             return True, time.perf_counter()  # ← Return timestamp, not latency!
#         except Exception as e:
#             _LOG.warning("CoAP PUT failed: %s", e)
#             return False, 0.0


# # Ensure the orchestrator can find the Protocol symbol
# __all__ = ["Protocol"]


"""
CoAP protocol plugin for STGen – active mode with detailed logging.
"""

import sys
import asyncio
import json
import logging
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from aiocoap import Context, Message, Code, resource
except ImportError as exc:
    raise ImportError(
        "aiocoap not installed – run:  pip install aiocoap[all]==0.4.7"
    ) from exc

# ensure stgen package is discoverable when run standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface

_LOG = logging.getLogger("coap")


# --------------------------------------------------------------------------- #
class SimpleResource(resource.Resource):
    """A basic CoAP resource that handles PUT requests with logging."""

    async def render_put(self, request):
        try:
            payload_str = request.payload.decode()
            data = json.loads(payload_str)
            _LOG.info("📥 SERVER RECEIVED: %s", json.dumps(data, indent=2))
        except Exception as e:
            _LOG.warning("Failed to parse received data: %s", e)
            _LOG.debug("Raw payload: %s", request.payload)
        
        return Message(code=Code.CHANGED, payload=b"OK")


# --------------------------------------------------------------------------- #
class Protocol(ProtocolInterface):
    """CoAP plug-in that satisfies STGen ProtocolInterface."""

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        self._ctx: Context | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lat: List[float] = []  # store latencies
        self._alive: bool = True
        self._msg_count: int = 0

    # ---------- life-cycle -------------------------------------------------- #
    def start_server(self) -> None:
        """Start aiocoap server in a dedicated thread."""
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        time.sleep(0.5)  # give the socket time to bind
        _LOG.info("CoAP server thread started")

    def start_clients(self, num: int) -> None:
        _LOG.info("CoAP: %d logical clients (implicit)", num)

    def stop(self) -> None:
        """Stop server and close event loop."""
        self._alive = False
        if self._loop and self._ctx:
            fut = asyncio.run_coroutine_threadsafe(self._ctx.shutdown(), self._loop)
            try:
                fut.result(2)
            except Exception as e:
                _LOG.warning("shutdown: %s", e)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        _LOG.info("CoAP server stopped")

    # ---------- active-mode send ------------------------------------------- #
    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """Thread-safe CoAP PUT + RTT measurement."""
        if not self._loop or not self._ctx:
            _LOG.error("CoAP context not ready")
            return False, 0.0
        
        self._msg_count += 1
        _LOG.info("📤 CLIENT [%s] SENDING (msg #%d): %s", 
                  client_id, self._msg_count, json.dumps(data, indent=2))
        
        future = asyncio.run_coroutine_threadsafe(self._send_async(data), self._loop)
        return future.result()

    # ---------- internal async --------------------------------------------- #
    def _build_site(self):
        root = resource.Site()

        class RootResource(resource.Resource):
            async def render_put(self, request):
                try:
                    payload_str = request.payload.decode()
                    data = json.loads(payload_str)
                    _LOG.info("📥 SERVER RECEIVED (root): %s", json.dumps(data, indent=2))
                except Exception as e:
                    _LOG.warning("Failed to parse received data: %s", e)
                return Message(code=Code.CHANGED, payload=b"OK")

        # Handle both '/' and '/data' so clients always get a reply
        root.add_resource([], RootResource())        # ← root path
        root.add_resource(['data'], SimpleResource())  # ← /data path
        return root

    def _run_server(self) -> None:
        """Run aiocoap event loop forever (in separate thread)."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._loop = asyncio.get_event_loop()
        try:
            self._ctx = self._loop.run_until_complete(
                Context.create_server_context(
                    self._build_site(),
                    bind=(self.cfg["server_ip"], self.cfg["server_port"]),
                )
            )
            _LOG.info(
                "CoAP server listening on %s:%s",
                self.cfg["server_ip"],
                self.cfg["server_port"],
            )
            self._loop.run_forever()
        finally:
            if self._ctx:
                self._loop.run_until_complete(self._ctx.shutdown())

    async def _send_async(self, data: Dict) -> Tuple[bool, float]:
        """Perform a CoAP PUT request and measure RTT."""
        uri = f'coap://{self.cfg["server_ip"]}:{self.cfg["server_port"]}/data'
        t0 = time.perf_counter()
        try:
            req = Message(
                code=Code.PUT,
                uri=uri,
                payload=json.dumps(data).encode(),
                content_format=0,  # text/plain
            )
            resp = await self._ctx.request(req).response
            latency_ms = (time.perf_counter() - t0) * 1000
            self._lat.append(latency_ms)
            _LOG.info(" CLIENT RECEIVED RESPONSE: code=%s, RTT=%.2fms", 
                     resp.code, latency_ms)
            return True, time.perf_counter()
        except Exception as e:
            _LOG.error(" CLIENT REQUEST FAILED: %s", e)
            return False, 0.0


# Ensure the orchestrator can find the Protocol symbol
__all__ = ["Protocol"]