"""远端中间件 SSH 隧道。

本地后端启动时，先通过 SSH 连接到服务器，再把远端 PostgreSQL
和 Elasticsearch 映射成本机端口。这样业务代码仍然只连本机地址，
但实际流量会走远端中间件。
"""

from __future__ import annotations

import socket
import socketserver
import threading
import time
from dataclasses import dataclass
from typing import Optional

import paramiko


class _ForwardHandler(socketserver.StreamRequestHandler):
    """单个连接的数据转发处理。"""

    def handle(self) -> None:
        transport = self.server.transport  # type: ignore[attr-defined]
        remote_host = self.server.remote_host  # type: ignore[attr-defined]
        remote_port = self.server.remote_port  # type: ignore[attr-defined]

        try:
            chan = transport.open_channel(
                "direct-tcpip",
                (remote_host, remote_port),
                self.request.getpeername(),
            )
        except Exception:
            return

        if chan is None:
            return

        try:
            # Windows 上直接把 Paramiko Channel 放进 select 容易不稳定。
            # 这里改成两条独立的搬运线程，避免 PostgreSQL 握手阶段被提前断开。
            stop_event = threading.Event()
            client_socket = self.request
            client_socket.settimeout(1.0)
            chan.settimeout(1.0)

            def forward(source, target, close_target: bool = False) -> None:
                try:
                    while not stop_event.is_set():
                        try:
                            data = source.recv(4096)
                        except TimeoutError:
                            continue
                        except OSError:
                            break

                        if not data:
                            break

                        try:
                            target.sendall(data)
                        except OSError:
                            break
                finally:
                    stop_event.set()
                    if close_target:
                        try:
                            target.close()
                        except Exception:
                            pass

            upstream = threading.Thread(
                target=forward,
                args=(client_socket, chan, True),
                daemon=True,
                name="ssh-tunnel-upstream",
            )
            downstream = threading.Thread(
                target=forward,
                args=(chan, client_socket, False),
                daemon=True,
                name="ssh-tunnel-downstream",
            )
            upstream.start()
            downstream.start()
            upstream.join()
            downstream.join()
        finally:
            try:
                chan.close()
            except Exception:
                pass


class _ForwardServer(socketserver.ThreadingTCPServer):
    """支持多连接的本地转发服务器。"""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, transport, remote_host, remote_port):
        super().__init__(server_address, RequestHandlerClass)
        self.transport = transport
        self.remote_host = remote_host
        self.remote_port = remote_port


@dataclass(slots=True)
class _TunnelSpec:
    """单个端口转发定义。"""

    name: str
    local_host: str
    local_port: int
    remote_host: str
    remote_port: int


class RemoteMiddlewareTunnels:
    """远端中间件 SSH 隧道管理器。"""

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_username: str,
        ssh_password: str,
        tunnel_specs: list[_TunnelSpec],
        auto_start_remote_services: bool = False,
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.tunnel_specs = tunnel_specs
        self.auto_start_remote_services = auto_start_remote_services
        self._client: Optional[paramiko.SSHClient] = None
        self._servers: list[_ForwardServer] = []
        self._threads: list[threading.Thread] = []
        self._closed = False

    def start(self) -> None:
        """建立 SSH 连接并启动本地端口转发。"""
        if not self.ssh_host or not self.ssh_username:
            raise ValueError("SSH 隧道配置不完整")

        # 默认只连接现有远端服务，不主动触发远端重建，避免误伤已有数据。
        if self.auto_start_remote_services:
            self._ensure_remote_services_ready()

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_username,
            password=self.ssh_password or None,
            allow_agent=False,
            look_for_keys=False,
            timeout=15,
            banner_timeout=15,
            auth_timeout=15,
        )
        transport = client.get_transport()
        if transport is None:
            client.close()
            raise RuntimeError("SSH transport 初始化失败")
        transport.set_keepalive(30)

        for spec in self.tunnel_specs:
            server = _ForwardServer(
                (spec.local_host, spec.local_port),
                _ForwardHandler,
                transport,
                spec.remote_host,
                spec.remote_port,
            )
            thread = threading.Thread(
                target=server.serve_forever,
                name=f"ssh-tunnel-{spec.name}",
                daemon=True,
            )
            thread.start()
            self._servers.append(server)
            self._threads.append(thread)

        self._client = client
        self._wait_for_tunnels_ready()

    def _wait_for_tunnels_ready(self, timeout_seconds: int = 20) -> None:
        """等待本地转发端口真正可用，避免后续初始化抢跑。"""
        deadline = time.time() + timeout_seconds
        pending = list(self.tunnel_specs)

        while pending and time.time() < deadline:
            ready: list[_TunnelSpec] = []
            for spec in pending:
                try:
                    with socket.create_connection((spec.local_host, spec.local_port), timeout=1.0):
                        ready.append(spec)
                except OSError:
                    continue
            pending = [spec for spec in pending if spec not in ready]
            if pending:
                time.sleep(0.5)

        if pending:
            names = ", ".join(f"{spec.name}:{spec.local_port}" for spec in pending)
            raise RuntimeError(f"本地隧道端口未在预期时间内就绪: {names}")

    def _ensure_remote_services_ready(self) -> None:
        """尽量触发远端中间件启动。"""
        if not self.ssh_host or not self.ssh_username:
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_username,
            password=self.ssh_password or None,
            allow_agent=False,
            look_for_keys=False,
            timeout=15,
            banner_timeout=15,
            auth_timeout=15,
        )
        try:
            # 这里调用远端启动脚本，不阻塞本地启动太久。
            stdin, stdout, stderr = client.exec_command("bash /opt/travel-middleware/start-middleware.sh >/tmp/travel-middleware-start.log 2>&1 & echo $!", timeout=10)
            _ = stdout.read()
            _ = stderr.read()
        finally:
            client.close()

    def close(self) -> None:
        """关闭全部隧道和 SSH 连接。"""
        if self._closed:
            return

        for server in self._servers:
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass
        for thread in self._threads:
            try:
                thread.join(timeout=2.0)
            except Exception:
                pass
        self._servers.clear()
        self._threads.clear()

        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._closed = True
