"""
NetPulse Layer-4 (L4) TCP Reverse Proxy Extension.

Demonstrates the Computer Networks distinction between:
- Layer-4 (Transport Layer): Raw TCP byte stream proxying (blind to HTTP headers, paths, cookies)
- Layer-7 (Application Layer): HTTP reverse proxying (inspects paths, methods, headers, status codes)

This module operates independently using asyncio streams and does not destabilize the core L7 proxy.
"""

import argparse
import asyncio
import logging
import sys
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [L4-TCP-PROXY] %(message)s",
)
logger = logging.getLogger("tcp_proxy")


class L4TCPProxy:
    """
    Lightweight, asynchronous Layer-4 TCP Stream Proxy.
    Distributes raw TCP connections across healthy backend targets.
    """

    def __init__(
        self,
        listen_host: str = "127.0.0.1",
        listen_port: int = 8081,
        targets: List[Tuple[str, int]] = None,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.targets = targets or [
            ("127.0.0.1", 5001),
            ("127.0.0.1", 5002),
            ("127.0.0.1", 5003),
        ]
        self._index = 0
        self.total_connections = 0
        self.active_connections = 0
        self.server = None

    def _select_target(self) -> Tuple[str, int]:
        """Round-robin selection over configured target endpoints."""
        target = self.targets[self._index % len(self.targets)]
        self._index += 1
        return target

    async def _pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Unidirectionally pipe raw bytes between sockets until EOF or error."""
        try:
            while not reader.at_eof():
                data = await reader.read(65536)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
    ):
        """Handles an incoming TCP client connection and bridges it to an upstream backend."""
        self.total_connections += 1
        self.active_connections += 1
        client_addr = client_writer.get_extra_info("peername")
        target_host, target_port = self._select_target()

        logger.info(
            f"Accepted TCP conn from {client_addr} -> forwarding to backend {target_host}:{target_port} "
            f"(active={self.active_connections})"
        )

        try:
            backend_reader, backend_writer = await asyncio.wait_for(
                asyncio.open_connection(target_host, target_port),
                timeout=3.0,
            )
        except Exception as exc:
            logger.error(f"Failed to connect to backend {target_host}:{target_port}: {exc}")
            client_writer.close()
            await client_writer.wait_closed()
            self.active_connections -= 1
            return

        try:
            # Bidirectional stream piping at Transport Layer
            await asyncio.gather(
                self._pipe(client_reader, backend_writer),
                self._pipe(backend_reader, client_writer),
            )
        finally:
            self.active_connections -= 1
            logger.info(f"Closed TCP conn from {client_addr} (active={self.active_connections})")

    async def start(self):
        """Starts the Layer-4 TCP Proxy server."""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.listen_host,
            self.listen_port,
        )
        logger.info(
            f"L4 TCP Proxy listening on {self.listen_host}:{self.listen_port} -> Targets: {self.targets}"
        )
        async with self.server:
            await self.server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="NetPulse Layer-4 TCP Proxy")
    parser.add_argument("--port", type=int, default=8081, help="Listen TCP port (default: 8081)")
    parser.add_argument("--host", default="127.0.0.1", help="Listen host (default: 127.0.0.1)")
    args = parser.parse_args()

    proxy = L4TCPProxy(listen_host=args.host, listen_port=args.port)
    try:
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        logger.info("L4 TCP Proxy stopped by user.")


if __name__ == "__main__":
    main()
