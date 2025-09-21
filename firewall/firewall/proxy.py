"""网络代理层，用于拦截并过滤 TCP/UDP 数据。"""
from __future__ import annotations

import asyncio
import contextlib
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from typing import Optional

from .engine import FirewallEngine
from .rules import MatchAction, MatchProtocol, PacketInfo


@dataclass
class ProxyConfig:
    """防火墙代理配置。"""

    listen_host: str = "0.0.0.0"
    listen_port: int = 9000
    target_host: str = "127.0.0.1"
    target_port: int = 8000
    enable_tcp: bool = True
    enable_udp: bool = False


class FirewallService:
    """封装 TCP/UDP 代理逻辑。"""

    def __init__(self, engine: FirewallEngine, config: Optional[ProxyConfig] = None, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.engine = engine
        self.config = config or ProxyConfig()
        self.loop = loop or asyncio.get_event_loop()
        self.tcp_server: Optional[asyncio.base_events.Server] = None
        self._udp_transport: Optional[asyncio.transports.DatagramTransport] = None
        self._udp_protocol: Optional[_UDPProxyProtocol] = None
        self._tasks: set[asyncio.Task] = set()

    # 生命周期
    async def start(self) -> None:
        if self.config.enable_tcp:
            self.tcp_server = await asyncio.start_server(
                self._handle_tcp_client,
                self.config.listen_host,
                self.config.listen_port,
            )
        if self.config.enable_udp:
            await self._start_udp()

    async def stop(self) -> None:
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()
            self.tcp_server = None
        if self._udp_transport:
            self._udp_transport.close()
            self._udp_transport = None
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()

    @property
    def running(self) -> bool:
        return bool(self.tcp_server or self._udp_transport)

    def update_config(self, config: ProxyConfig) -> None:
        self.config = config

    # TCP 处理
    async def _handle_tcp_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        sock = writer.get_extra_info("sockname")
        if peer is None or sock is None:
            writer.close()
            await writer.wait_closed()
            return

        src_ip, src_port = peer[0], peer[1]
        dst_ip, dst_port = sock[0], sock[1]
        packet = PacketInfo(MatchProtocol.TCP, src_ip, src_port, dst_ip, dst_port)
        action, rule, source = self.engine.evaluate(packet)
        rule_name = rule.name if rule else source
        self.engine.create_log_record(packet, action, rule_name, "connection request")
        if action is not MatchAction.ALLOW:
            writer.close()
            await writer.wait_closed()
            return

        try:
            target_reader, target_writer = await asyncio.open_connection(
                self.config.target_host, self.config.target_port
            )
        except OSError as exc:
            self.engine.create_log_record(packet, MatchAction.DENY, "proxy", f"connect failed: {exc}")
            writer.close()
            await writer.wait_closed()
            return

        async def forward_data(src_reader: StreamReader, dst_writer: StreamWriter, direction: str) -> None:
            try:
                while True:
                    data = await src_reader.read(4096)
                    if not data:
                        break
                    packet = PacketInfo(
                        MatchProtocol.TCP,
                        src_ip if direction == "client_to_server" else self.config.target_host,
                        src_port if direction == "client_to_server" else self.config.target_port,
                        dst_ip if direction == "client_to_server" else src_ip,
                        dst_port if direction == "client_to_server" else src_port,
                        data,
                    )
                    action, rule, source = self.engine.evaluate(packet)
                    rule_name = rule.name if rule else source
                    self.engine.create_log_record(packet, action, rule_name, direction)
                    if action is MatchAction.ALLOW:
                        dst_writer.write(data)
                        await dst_writer.drain()
                    else:
                        break
            except asyncio.CancelledError:
                pass
            finally:
                dst_writer.close()
                try:
                    await dst_writer.wait_closed()
                except Exception:  # pragma: no cover - 关闭异常忽略
                    pass

        client_to_server = self.loop.create_task(forward_data(reader, target_writer, "client_to_server"))
        server_to_client = self.loop.create_task(forward_data(target_reader, writer, "server_to_client"))
        self._tasks.update({client_to_server, server_to_client})
        try:
            await asyncio.wait(
                [client_to_server, server_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in (client_to_server, server_to_client):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            writer.close()
            await writer.wait_closed()

    # UDP 处理
    async def _start_udp(self) -> None:
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: _UDPProxyProtocol(self.engine, self.config),
            local_addr=(self.config.listen_host, self.config.listen_port),
        )
        self._udp_transport = transport
        self._udp_protocol = protocol


class _UDPProxyProtocol(asyncio.DatagramProtocol):
    """UDP 代理协议实现。"""

    def __init__(self, engine: FirewallEngine, config: ProxyConfig) -> None:
        self.engine = engine
        self.config = config
        self.transport: Optional[asyncio.transports.DatagramTransport] = None
        self._upstream_transport: Optional[asyncio.transports.DatagramTransport] = None
        self._client_addresses: set[tuple[str, int]] = set()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]
        loop = asyncio.get_running_loop()
        loop.create_task(self._setup_upstream())

    async def _setup_upstream(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _UDPUpstreamProtocol(self),
            remote_addr=(self.config.target_host, self.config.target_port),
        )
        self._upstream_transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        packet = PacketInfo(
            MatchProtocol.UDP,
            addr[0],
            addr[1],
            self.config.target_host,
            self.config.target_port,
            data,
        )
        action, rule, source = self.engine.evaluate(packet)
        rule_name = rule.name if rule else source
        self.engine.create_log_record(packet, action, rule_name, "udp inbound")
        if action is MatchAction.ALLOW and self._upstream_transport:
            self._client_addresses.add(addr)
            self._upstream_transport.sendto(data)

    def error_received(self, exc: Exception) -> None:  # pragma: no cover - 框架回调
        self.engine.logger.error("UDP error: %s", exc)

    def connection_lost(self, exc: Optional[Exception]) -> None:  # pragma: no cover - 框架回调
        if exc:
            self.engine.logger.error("UDP connection lost: %s", exc)
        self._client_addresses.clear()

    def handle_upstream(self, data: bytes) -> None:
        if not self.transport:
            return
        for client in self._client_addresses:
            self.transport.sendto(data, client)


class _UDPUpstreamProtocol(asyncio.DatagramProtocol):
    """接收来自后端服务器的 UDP 响应。"""

    def __init__(self, parent: _UDPProxyProtocol) -> None:
        self.parent = parent

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:  # pragma: no cover - 简单转发
        self.parent.handle_upstream(data)
