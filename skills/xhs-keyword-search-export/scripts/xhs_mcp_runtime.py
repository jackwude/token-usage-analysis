#!/usr/bin/env python3
from __future__ import annotations

import atexit
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
from dataclasses import dataclass


DOCKER_APP = "/Applications/Docker.app"
CONTAINER_NAME = "xiaohongshu-mcp"
IMAGE = "xpzouying/xiaohongshu-mcp:latest"
PORT = 18060
MCP_URL = f"http://127.0.0.1:{PORT}/mcp"


@dataclass
class RuntimeState:
    docker_was_running: bool = False
    docker_started_by_us: bool = False
    container_was_running: bool = False
    container_started_by_us: bool = False
    cleanup_registered: bool = False
    cleanup_mode: str = "force-kill"


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}


_STATE = RuntimeState(
    docker_was_running=_env_bool("XHS_DOCKER_WAS_RUNNING", False),
    docker_started_by_us=_env_bool("XHS_DOCKER_STARTED_BY_US", False),
    container_was_running=_env_bool("XHS_CONTAINER_WAS_RUNNING", False),
    container_started_by_us=_env_bool("XHS_CONTAINER_STARTED_BY_US", False),
)


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _docker_running() -> bool:
    p = subprocess.run(["docker", "info"], capture_output=True, text=True)
    return p.returncode == 0


def _wait_docker_stable(timeout_s: int = 180, settle_s: int = 8) -> None:
    deadline = time.time() + timeout_s
    stable_since = None
    last_err = ""
    while time.time() < deadline:
        info = subprocess.run(["docker", "info"], capture_output=True, text=True)
        ps = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
        if info.returncode == 0 and ps.returncode == 0:
            if stable_since is None:
                stable_since = time.time()
            if time.time() - stable_since >= settle_s:
                return
        else:
            stable_since = None
            last_err = (info.stderr or ps.stderr or info.stdout or ps.stdout or "docker not ready").strip()
        time.sleep(3)
    raise RuntimeError(f"Docker Desktop 启动后未稳定就绪: {last_err}")


def _start_docker_desktop(timeout_s: int = 180) -> bool:
    if _docker_running():
        _wait_docker_stable(timeout_s=60, settle_s=5)
        return False
    # 尝试启动 Docker Desktop，最多只试一次
    subprocess.run(["open", "-a", DOCKER_APP], check=False)
    try:
        _wait_docker_stable(timeout_s=timeout_s, settle_s=8)
        return True
    except RuntimeError:
        # 启动失败时不抛出，让上层处理
        # 这表示本次任务无法自动完成环境准备
        raise


def _container_running() -> bool:
    p = _run(["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME], check=False)
    return p.returncode == 0 and p.stdout.strip() == "true"


def _container_exists() -> bool:
    p = _run(["docker", "inspect", CONTAINER_NAME], check=False)
    return p.returncode == 0


def _start_container() -> bool:
    if _container_running():
        return False
    if _container_exists():
        _run(["docker", "start", CONTAINER_NAME])
        return True
    _run([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{PORT}:{PORT}",
        IMAGE,
    ])
    return True


def _wait_http_ready(url: str = MCP_URL, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    last_err = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status < 500:
                    return
        except urllib.error.HTTPError as e:
            # 某些 MCP HTTP 端点在未带协议 payload 的 GET 探活时会返回 400，
            # 这说明服务已启动、只是请求格式不对；可视为 ready。
            if e.code < 500:
                return
            last_err = f"HTTP Error {e.code}: {e.reason}"
        except Exception as e:
            last_err = str(e)
        time.sleep(2)
    raise RuntimeError(f"xiaohongshu MCP 未在超时内就绪: {last_err}")


def _quit_docker_desktop() -> None:
    subprocess.run(["osascript", "-e", 'quit app "Docker"'], check=False)


def _kill_docker_processes() -> None:
    patterns = [
        "Docker Desktop",
        "com.docker.backend",
        "docker-sandbox",
        "Docker Desktop Helper",
    ]
    for pat in patterns:
        subprocess.run(["pkill", "-f", pat], check=False)


def _stop_container() -> None:
    subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True, text=True, check=False)


def _list_running_containers() -> list[str]:
    p = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
    if p.returncode != 0:
        return []
    return [line.strip() for line in (p.stdout or "").splitlines() if line.strip()]


def _should_smart_cleanup() -> bool:
    names = _list_running_containers()
    if not names:
        return True
    return names == [CONTAINER_NAME]


def _cleanup() -> None:
    # 任务结束后统一回收 xiaohongshu-mcp，并强退 Docker Desktop。
    # 顺序：停容器 -> quit app -> 等待 -> 定向 kill 残留进程。
    if _container_running() or _container_exists():
        _stop_container()
    _quit_docker_desktop()
    time.sleep(4)
    _kill_docker_processes()


def cleanup_xhs_mcp() -> None:
    _cleanup()


def ensure_xhs_mcp() -> RuntimeState:
    _STATE.docker_was_running = _docker_running()
    if not _STATE.docker_was_running:
        _STATE.docker_started_by_us = _start_docker_desktop()

    _STATE.container_was_running = _container_running()
    if not _STATE.container_was_running:
        _STATE.container_started_by_us = _start_container()

    _wait_http_ready()

    os.environ["XHS_DOCKER_WAS_RUNNING"] = "1" if _STATE.docker_was_running else "0"
    os.environ["XHS_DOCKER_STARTED_BY_US"] = "1" if _STATE.docker_started_by_us else "0"
    os.environ["XHS_CONTAINER_WAS_RUNNING"] = "1" if _STATE.container_was_running else "0"
    os.environ["XHS_CONTAINER_STARTED_BY_US"] = "1" if _STATE.container_started_by_us else "0"

    if not _STATE.cleanup_registered:
        atexit.register(_cleanup)
        _STATE.cleanup_registered = True
    return _STATE


def runtime_summary() -> str:
    return json.dumps({
        "docker_was_running": _STATE.docker_was_running,
        "docker_started_by_us": _STATE.docker_started_by_us,
        "container_was_running": _STATE.container_was_running,
        "container_started_by_us": _STATE.container_started_by_us,
        "cleanup_mode": _STATE.cleanup_mode,
        "mcp_url": MCP_URL,
    }, ensure_ascii=False)
