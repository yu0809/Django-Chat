"""防火墙规则定义与匹配工具。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import ip_address, ip_network
import re
from typing import Optional, Pattern


class MatchProtocol(str, Enum):
    """协议匹配枚举。"""

    ANY = "ANY"
    TCP = "TCP"
    UDP = "UDP"


class MatchAction(str, Enum):
    """规则动作类型。"""

    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(slots=True)
class PacketInfo:
    """封装需要匹配的包信息。"""

    protocol: MatchProtocol
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    payload: bytes = b""

    def payload_text(self, encoding: str = "utf-8", errors: str = "ignore") -> str:
        """以文本形式返回负载，便于进行正则匹配。"""

        if not self.payload:
            return ""
        return self.payload.decode(encoding, errors)


@dataclass(slots=True)
class AddressPattern:
    """白名单/黑名单中使用的地址描述。"""

    ip: Optional[str] = None
    port: Optional[str] = None

    def matches(self, packet: PacketInfo) -> bool:
        return _match_ip(packet.src_ip, self.ip) and _match_port(packet.src_port, self.port)


@dataclass(slots=True)
class FirewallRule:
    """防火墙规则定义。"""

    name: str
    action: MatchAction
    protocol: MatchProtocol = MatchProtocol.ANY
    src_ip: Optional[str] = None
    src_port: Optional[str] = None
    dst_ip: Optional[str] = None
    dst_port: Optional[str] = None
    pattern: Optional[str] = None
    description: str = ""
    _compiled_pattern: Optional[Pattern[str]] = field(default=None, init=False, repr=False)

    def matches(self, packet: PacketInfo) -> bool:
        """判断规则是否命中。"""

        if self.protocol is not MatchProtocol.ANY and packet.protocol is not self.protocol:
            return False
        if not _match_ip(packet.src_ip, self.src_ip):
            return False
        if not _match_ip(packet.dst_ip, self.dst_ip):
            return False
        if not _match_port(packet.src_port, self.src_port):
            return False
        if not _match_port(packet.dst_port, self.dst_port):
            return False
        if self.pattern:
            pattern = self._compiled_pattern or re.compile(self.pattern)
            self._compiled_pattern = pattern
            payload_text = packet.payload_text()
            if not pattern.search(payload_text):
                return False
        return True


def _match_ip(value: str, condition: Optional[str]) -> bool:
    """根据条件匹配 IP 地址。"""

    if not condition or condition in {"*", "any", "ANY"}:
        return True
    condition = condition.strip()
    if "/" in condition:
        try:
            network = ip_network(condition, strict=False)
        except ValueError:
            return False
        try:
            return ip_address(value) in network
        except ValueError:
            return False
    return value == condition


def _match_port(value: int, condition: Optional[str]) -> bool:
    """根据字符串条件匹配端口。

    支持格式：
    - ``None`` 或 ``"*"`` 表示任意端口；
    - 单个端口（例如 ``"80"``）；
    - 端口范围 ``"8000-8100"``；
    - 多个端口使用逗号分隔 ``"80,443"``。
    """

    if not condition or condition in {"*", "any", "ANY"}:
        return True
    for token in (part.strip() for part in condition.split(",")):
        if "-" in token:
            start, _, end = token.partition("-")
            if start.isdigit() and end.isdigit():
                if int(start) <= value <= int(end):
                    return True
        elif token.isdigit():
            if value == int(token):
                return True
    return False
