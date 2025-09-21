"""Tkinter 图形界面。"""
from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from concurrent.futures import Future
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Coroutine, Optional

from .engine import FirewallEngine
from .proxy import FirewallService, ProxyConfig
from .rules import AddressPattern, FirewallRule, MatchAction, MatchProtocol


class AsyncioThread(threading.Thread):
    """在后台线程中运行 asyncio 事件循环。"""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self) -> None:  # pragma: no cover - 线程启动逻辑
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)

    def run_coroutine(self, coro: Coroutine[Any, Any, Any]) -> Future:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


class FirewallApp:
    """应用主界面。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("简易防火墙")
        self.engine = FirewallEngine()
        self.config = ProxyConfig()
        self.loop_thread = AsyncioThread()
        self.loop_thread.start()
        self.service = FirewallService(self.engine, self.config, loop=self.loop_thread.loop)

        self._build_ui()
        self._refresh_rule_list()
        self._schedule_log_refresh()

    # UI 构建
    def _build_ui(self) -> None:
        self.root.geometry("960x640")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        config_frame = ttk.LabelFrame(self.root, text="代理配置")
        config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for i in range(6):
            config_frame.columnconfigure(i, weight=1)

        ttk.Label(config_frame, text="监听地址").grid(row=0, column=0, padx=5, pady=5)
        self.listen_host_var = tk.StringVar(value=self.config.listen_host)
        ttk.Entry(config_frame, textvariable=self.listen_host_var, width=15).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(config_frame, text="监听端口").grid(row=0, column=2, padx=5, pady=5)
        self.listen_port_var = tk.StringVar(value=str(self.config.listen_port))
        ttk.Entry(config_frame, textvariable=self.listen_port_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(config_frame, text="后端地址").grid(row=0, column=4, padx=5, pady=5)
        self.target_host_var = tk.StringVar(value=self.config.target_host)
        ttk.Entry(config_frame, textvariable=self.target_host_var, width=15).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(config_frame, text="后端端口").grid(row=0, column=6, padx=5, pady=5)
        self.target_port_var = tk.StringVar(value=str(self.config.target_port))
        ttk.Entry(config_frame, textvariable=self.target_port_var, width=10).grid(row=0, column=7, padx=5, pady=5)

        self.enable_tcp_var = tk.BooleanVar(value=self.config.enable_tcp)
        ttk.Checkbutton(config_frame, text="启用 TCP", variable=self.enable_tcp_var).grid(row=1, column=0, padx=5, pady=5)
        self.enable_udp_var = tk.BooleanVar(value=self.config.enable_udp)
        ttk.Checkbutton(config_frame, text="启用 UDP", variable=self.enable_udp_var).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(config_frame, text="默认策略").grid(row=1, column=2, padx=5, pady=5)
        self.default_action_var = tk.StringVar(value=self.engine.default_action.value)
        default_menu = ttk.OptionMenu(
            config_frame,
            self.default_action_var,
            self.engine.default_action.value,
            *[action.value for action in MatchAction],
            command=lambda _: self._change_default_action(),
        )
        default_menu.grid(row=1, column=3, padx=5, pady=5)

        start_button = ttk.Button(config_frame, text="启动防火墙", command=self.start_firewall)
        start_button.grid(row=1, column=4, padx=5, pady=5)
        stop_button = ttk.Button(config_frame, text="停止防火墙", command=self.stop_firewall)
        stop_button.grid(row=1, column=5, padx=5, pady=5)

        rule_frame = ttk.LabelFrame(self.root, text="规则管理")
        rule_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        rule_frame.columnconfigure(0, weight=1)
        rule_frame.rowconfigure(0, weight=1)

        columns = ("name", "action", "protocol", "src", "dst", "pattern")
        self.rule_tree = ttk.Treeview(rule_frame, columns=columns, show="headings")
        headings = {
            "name": "名称",
            "action": "动作",
            "protocol": "协议",
            "src": "源",
            "dst": "目的",
            "pattern": "特征",
        }
        for column in columns:
            self.rule_tree.heading(column, text=headings[column])
            self.rule_tree.column(column, width=120, anchor=tk.CENTER)
        self.rule_tree.grid(row=0, column=0, sticky="nsew")

        rule_btn_frame = ttk.Frame(rule_frame)
        rule_btn_frame.grid(row=1, column=0, sticky="ew", pady=5)
        ttk.Button(rule_btn_frame, text="新增规则", command=self.add_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(rule_btn_frame, text="删除规则", command=self.remove_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(rule_btn_frame, text="添加白名单", command=lambda: self._add_list_entry(True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(rule_btn_frame, text="添加黑名单", command=lambda: self._add_list_entry(False)).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(self.root, text="实时日志")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="none")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)

    # 防火墙控制
    def _collect_config(self) -> Optional[ProxyConfig]:
        try:
            return ProxyConfig(
                listen_host=self.listen_host_var.get(),
                listen_port=int(self.listen_port_var.get()),
                target_host=self.target_host_var.get(),
                target_port=int(self.target_port_var.get()),
                enable_tcp=self.enable_tcp_var.get(),
                enable_udp=self.enable_udp_var.get(),
            )
        except ValueError:
            messagebox.showerror("输入错误", "端口必须为整数")
            return None

    def start_firewall(self) -> None:
        if self.service.running:
            messagebox.showinfo("提示", "防火墙已在运行")
            return
        config = self._collect_config()
        if not config:
            return
        self.config = config
        self.service.update_config(config)
        future = self.loop_thread.run_coroutine(self.service.start())
        future.add_done_callback(lambda f: self._handle_future_result(f, "启动防火墙"))

    def stop_firewall(self) -> None:
        if not self.service.running:
            return
        future = self.loop_thread.run_coroutine(self.service.stop())
        future.add_done_callback(lambda f: self._handle_future_result(f, "停止防火墙"))

    def _handle_future_result(self, future: Future, action: str) -> None:
        try:
            future.result()
        except Exception as exc:  # pragma: no cover - UI 异常提示
            self.root.after(0, lambda: messagebox.showerror("错误", f"{action}失败: {exc}"))

    def _change_default_action(self) -> None:
        value = self.default_action_var.get()
        self.engine.set_default_action(MatchAction(value))

    # 规则管理
    def add_rule(self) -> None:
        name = simpledialog.askstring("新增规则", "规则名称:")
        if not name:
            return
        action_value = simpledialog.askstring("新增规则", "动作(ALLOW/DENY):", initialvalue="DENY")
        if not action_value:
            return
        protocol_value = simpledialog.askstring("新增规则", "协议(ANY/TCP/UDP):", initialvalue="ANY")
        src_ip = simpledialog.askstring("新增规则", "源IP(可选):")
        src_port = simpledialog.askstring("新增规则", "源端口(可选):")
        dst_ip = simpledialog.askstring("新增规则", "目的IP(可选):")
        dst_port = simpledialog.askstring("新增规则", "目的端口(可选):")
        pattern = simpledialog.askstring("新增规则", "内容特征(正则，可选):")
        try:
            rule = FirewallRule(
                name=name,
                action=MatchAction(action_value.upper()),
                protocol=MatchProtocol(protocol_value.upper()),
                src_ip=src_ip or None,
                src_port=src_port or None,
                dst_ip=dst_ip or None,
                dst_port=dst_port or None,
                pattern=pattern or None,
            )
        except ValueError:
            messagebox.showerror("输入错误", "动作或协议不合法")
            return
        self.engine.add_rule(rule)
        self._refresh_rule_list()

    def remove_rule(self) -> None:
        selection = self.rule_tree.selection()
        if not selection:
            return
        name = self.rule_tree.item(selection[0], "values")[0]
        if self.engine.remove_rule(name):
            self._refresh_rule_list()

    def _add_list_entry(self, whitelist: bool) -> None:
        ip_value = simpledialog.askstring("名单", "IP (可为CIDR，可为空):")
        port_value = simpledialog.askstring("名单", "端口(可为空):")
        pattern = AddressPattern(ip_value or None, port_value or None)
        if whitelist:
            self.engine.add_whitelist(pattern)
        else:
            self.engine.add_blacklist(pattern)

    def _refresh_rule_list(self) -> None:
        for item in self.rule_tree.get_children():
            self.rule_tree.delete(item)
        for rule in self.engine.rules:
            src = f"{rule.src_ip or '*'}:{rule.src_port or '*'}"
            dst = f"{rule.dst_ip or '*'}:{rule.dst_port or '*'}"
            self.rule_tree.insert(
                "",
                tk.END,
                values=(
                    rule.name,
                    rule.action.value,
                    rule.protocol.value,
                    src,
                    dst,
                    rule.pattern or "-",
                ),
            )

    # 日志刷新
    def _schedule_log_refresh(self) -> None:
        self._update_logs()
        self.root.after(1000, self._schedule_log_refresh)

    def _update_logs(self) -> None:
        logs = self.engine.recent_logs()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        for record in logs[-200:]:
            text = (
                f"[{record.timestamp:%H:%M:%S}] {record.action.value} "
                f"{record.packet.src_ip}:{record.packet.src_port} -> {record.packet.dst_ip}:{record.packet.dst_port} "
                f"via {record.rule_name} ({record.message})\n"
            )
            self.log_text.insert(tk.END, text)
        self.log_text.configure(state="disabled")

    def on_close(self) -> None:
        if self.service.running:
            future = self.loop_thread.run_coroutine(self.service.stop())
            future.result(timeout=5)
        self.loop_thread.stop()
        self.root.destroy()


def launch_gui() -> None:
    root = tk.Tk()
    app = FirewallApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


__all__ = ["launch_gui", "FirewallApp"]
