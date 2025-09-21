"""防火墙规则引擎实现。"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Deque, Iterable, List, Optional, Tuple

from .rules import AddressPattern, FirewallRule, MatchAction, PacketInfo


@dataclass(slots=True)
class FirewallLogRecord:
    """防火墙日志记录。"""

    timestamp: datetime
    packet: PacketInfo
    action: MatchAction
    rule_name: str
    message: str

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
            "src": f"{self.packet.src_ip}:{self.packet.src_port}",
            "dst": f"{self.packet.dst_ip}:{self.packet.dst_port}",
            "protocol": self.packet.protocol.value,
            "action": self.action.value,
            "rule": self.rule_name,
            "message": self.message,
        }


class FirewallEngine:
    """管理规则、白名单和黑名单，并对数据包进行判决。"""

    def __init__(self, default_action: MatchAction = MatchAction.DENY, log_limit: int = 1000) -> None:
        self.rules: List[FirewallRule] = []
        self.whitelist: List[AddressPattern] = []
        self.blacklist: List[AddressPattern] = []
        self.default_action = default_action
        self._log: Deque[FirewallLogRecord] = deque(maxlen=log_limit)
        self.logger = logging.getLogger("simple_firewall")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    # 规则管理
    def add_rule(self, rule: FirewallRule, index: Optional[int] = None) -> None:
        if index is None:
            self.rules.append(rule)
        else:
            self.rules.insert(index, rule)

    def remove_rule(self, name: str) -> bool:
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                del self.rules[i]
                return True
        return False

    def clear_rules(self) -> None:
        self.rules.clear()

    def extend_rules(self, rules: Iterable[FirewallRule]) -> None:
        for rule in rules:
            self.add_rule(rule)

    # 白名单黑名单
    def add_whitelist(self, pattern: AddressPattern) -> None:
        self.whitelist.append(pattern)

    def add_blacklist(self, pattern: AddressPattern) -> None:
        self.blacklist.append(pattern)

    def clear_whitelist(self) -> None:
        self.whitelist.clear()

    def clear_blacklist(self) -> None:
        self.blacklist.clear()

    def set_default_action(self, action: MatchAction) -> None:
        self.default_action = action

    # 判决逻辑
    def evaluate(self, packet: PacketInfo) -> Tuple[MatchAction, Optional[FirewallRule], str]:
        for item in self.whitelist:
            if item.matches(packet):
                return MatchAction.ALLOW, None, "whitelist"
        for item in self.blacklist:
            if item.matches(packet):
                return MatchAction.DENY, None, "blacklist"
        for rule in self.rules:
            if rule.matches(packet):
                return rule.action, rule, "rule"
        return self.default_action, None, "default"

    # 日志
    def log_packet(self, record: FirewallLogRecord) -> None:
        self._log.append(record)
        self.logger.info(
            "%s %s -> %s by %s (%s)",
            record.action.value,
            f"{record.packet.src_ip}:{record.packet.src_port}",
            f"{record.packet.dst_ip}:{record.packet.dst_port}",
            record.rule_name,
            record.message,
        )

    def create_log_record(
        self,
        packet: PacketInfo,
        action: MatchAction,
        rule_name: str,
        message: str = "",
    ) -> FirewallLogRecord:
        record = FirewallLogRecord(datetime.now(), packet, action, rule_name, message)
        self.log_packet(record)
        return record

    def recent_logs(self) -> List[FirewallLogRecord]:
        return list(self._log)

    def export_logs(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for record in self._log:
                f.write(str(record.as_dict()) + "\n")

    def attach_file_logger(self, path: Path) -> None:
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(file_handler)

    def load_rules_from_dicts(self, items: Iterable[dict]) -> None:
        for item in items:
            rule = FirewallRule(
                name=item.get("name", "rule"),
                action=MatchAction(item.get("action", MatchAction.DENY.value)),
                protocol=MatchProtocol(item.get("protocol", MatchProtocol.ANY.value)),
                src_ip=item.get("src_ip"),
                src_port=item.get("src_port"),
                dst_ip=item.get("dst_ip"),
                dst_port=item.get("dst_port"),
                pattern=item.get("pattern"),
                description=item.get("description", ""),
            )
            self.add_rule(rule)


# 避免循环导入
from .rules import MatchProtocol  # noqa: E402
