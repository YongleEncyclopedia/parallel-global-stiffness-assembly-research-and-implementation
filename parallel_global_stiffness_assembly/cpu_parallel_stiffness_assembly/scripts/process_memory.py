#!/usr/bin/env python3
"""Run one child process and report its platform-specific peak memory."""

from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from typing import Any

if sys.platform != "win32":
    import resource


_CHILD_CLEANUP_TIMEOUT_SECONDS = 5.0


def _bytes_to_mb(value: int) -> float:
    return float(value) / (1024.0 * 1024.0)


def _posix_peak_rss_payload() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    if sys.platform == "darwin":
        peak_mb = float(usage.ru_maxrss) / (1024.0 * 1024.0)
    else:
        peak_mb = float(usage.ru_maxrss) / 1024.0
    return {
        "peak_rss_mb": peak_mb,
        "memory_metric": "process_ru_maxrss",
        "measurement_source": "resource.getrusage(RUSAGE_CHILDREN).ru_maxrss",
        "peak_working_set_mb": "",
        "peak_private_bytes_mb": "",
    }


if sys.platform == "win32":
    DWORD = ctypes.c_ulong
    SIZE_T = ctypes.c_size_t

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", DWORD),
            ("PageFaultCount", DWORD),
            ("PeakWorkingSetSize", SIZE_T),
            ("WorkingSetSize", SIZE_T),
            ("QuotaPeakPagedPoolUsage", SIZE_T),
            ("QuotaPagedPoolUsage", SIZE_T),
            ("QuotaPeakNonPagedPoolUsage", SIZE_T),
            ("QuotaNonPagedPoolUsage", SIZE_T),
            ("PagefileUsage", SIZE_T),
            ("PeakPagefileUsage", SIZE_T),
            ("PrivateUsage", SIZE_T),
        ]

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    kernel32.OpenProcess.argtypes = [DWORD, ctypes.c_int, DWORD]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int


def _last_windows_error() -> OSError:
    return ctypes.WinError(ctypes.get_last_error())


def _open_windows_process(pid: int) -> int:
    for access in (
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ,
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
    ):
        handle = kernel32.OpenProcess(access, 0, pid)
        if handle:
            return int(handle)
    raise ctypes.WinError(ctypes.get_last_error())


def _query_windows_process_memory(handle: int) -> dict[str, float]:
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_mb": _bytes_to_mb(int(counters.WorkingSetSize)),
        "peak_working_set_mb": _bytes_to_mb(int(counters.PeakWorkingSetSize)),
        "private_bytes_mb": _bytes_to_mb(int(counters.PrivateUsage)),
        "peak_private_bytes_mb": _bytes_to_mb(int(counters.PeakPagefileUsage)),
    }


def _terminate_and_reap(process: Any) -> None:
    if process.poll() is not None:
        process.wait()
        return
    process.terminate()
    try:
        process.wait(timeout=_CHILD_CLEANUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_windows_child(command: list[str]) -> tuple[int, dict[str, Any]]:
    process = subprocess.Popen(command)
    handle: int | None = None
    primary_error: BaseException | None = None
    peak_working_set_mb = 0.0
    peak_private_bytes_mb = 0.0
    try:
        handle = _open_windows_process(process.pid)
        while True:
            memory = _query_windows_process_memory(handle)
            peak_working_set_mb = max(
                peak_working_set_mb,
                memory["peak_working_set_mb"],
                memory["working_set_mb"],
            )
            peak_private_bytes_mb = max(
                peak_private_bytes_mb,
                memory["peak_private_bytes_mb"],
                memory["private_bytes_mb"],
            )
            if process.poll() is not None:
                break
            time.sleep(0.02)
        returncode = process.wait()
        return returncode, {
            "peak_rss_mb": peak_working_set_mb,
            "memory_metric": "windows_peak_working_set",
            "measurement_source": "GetProcessMemoryInfo.PeakWorkingSetSize",
            "peak_working_set_mb": peak_working_set_mb,
            "peak_private_bytes_mb": peak_private_bytes_mb,
        }
    except BaseException as error:
        primary_error = error
        try:
            _terminate_and_reap(process)
        except BaseException:
            pass
        raise
    finally:
        if handle is not None:
            try:
                closed = kernel32.CloseHandle(handle)
                if not closed and primary_error is None:
                    raise _last_windows_error()
            except BaseException:
                if primary_error is None:
                    raise


def run_child_with_memory(command: list[str]) -> tuple[int, dict[str, Any]]:
    """Run *command* once and return its exit code plus peak-memory payload."""

    if sys.platform == "win32":
        return _run_windows_child(command)
    completed = subprocess.run(command)
    return completed.returncode, _posix_peak_rss_payload()
