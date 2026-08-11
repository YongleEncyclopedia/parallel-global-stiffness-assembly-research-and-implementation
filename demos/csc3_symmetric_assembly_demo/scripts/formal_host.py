#!/usr/bin/env python3
"""收集并检查 Linux 正式实验主机的 CPU 拓扑和运行环境。

模块区分逻辑处理器、物理核心和 SMT，并提供固定的编译器、OpenMP 绑定与环境
变量检查，供正式实验脚本记录和复核。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union


CANONICAL_FORMAL_ENVIRONMENT: Dict[str, str] = {
    "LC_ALL": "C",
    "TZ": "UTC",
    "CC": "/usr/bin/gcc",
    "CXX": "/usr/bin/g++",
    "OMP_DYNAMIC": "false",
    "OMP_PROC_BIND": "close",
    "OMP_PLACES": "cores",
}

FORMAL_ENVIRONMENT_POLLUTION: Tuple[str, ...] = (
    "OMP_NUM_THREADS",
    "OMP_THREAD_LIMIT",
    "GOMP_CPU_AFFINITY",
    "KMP_AFFINITY",
    "PYTHONOPTIMIZE",
    "PYTHONPATH",
    "PYTHONHOME",
)

CONFLICTING_OPENMP_ENVIRONMENT: Tuple[str, ...] = (
    "OMP_NUM_THREADS",
    "OMP_THREAD_LIMIT",
    "GOMP_CPU_AFFINITY",
    "KMP_AFFINITY",
)


def conflicting_formal_environment_keys(
    environment: Mapping[str, str],
) -> Tuple[str, ...]:
    """Return a stable key-only snapshot of inherited formal conflicts."""

    return tuple(
        sorted(name for name in CONFLICTING_OPENMP_ENVIRONMENT if name in environment)
    )


@dataclass(frozen=True)
class LinuxCpuTopology:
    """One deterministic snapshot of Linux online, affinity, and core facts."""

    online_cpu_ids: Tuple[int, ...]
    affinity_cpu_ids: Tuple[int, ...]
    physical_core_ids: Tuple[Tuple[int, int], ...]
    full_host_affinity: bool
    errors: Tuple[str, ...] = ()

    @property
    def logical_cpu_count(self) -> int:
        return len(self.online_cpu_ids)

    @property
    def topology_complete(self) -> bool:
        return bool(self.online_cpu_ids) and bool(self.physical_core_ids) and not self.errors

    @property
    def physical_core_count(self) -> Optional[int]:
        if not self.topology_complete:
            return None
        return len(self.physical_core_ids)


def parse_cpu_list(text: str) -> Tuple[int, ...]:
    """Parse Linux CPU-list syntax such as ``0-3,8,10-11`` strictly."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("CPU list must be nonempty text")
    cpus = set()
    for raw_part in text.strip().split(","):
        part = raw_part.strip()
        if not part:
            raise ValueError("CPU list contains an empty item")
        if "-" in part:
            bounds = part.split("-", 1)
            if any(re.fullmatch(r"[0-9]+", bound.strip()) is None for bound in bounds):
                raise ValueError(f"invalid CPU range: {part!r}")
            first, last = (int(bound.strip()) for bound in bounds)
            if first > last:
                raise ValueError(f"reversed CPU range: {part!r}")
            cpus.update(range(first, last + 1))
        else:
            if re.fullmatch(r"[0-9]+", part) is None:
                raise ValueError(f"invalid CPU identifier: {part!r}")
            cpus.add(int(part))
    if not cpus:
        raise ValueError("CPU list contains no processors")
    return tuple(sorted(cpus))


def _topology_identifier(text: str, label: str) -> int:
    value = text.strip()
    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError(f"{label} is not a nonnegative integer")
    return int(value)


def _online_cpu_ids(
    root: Path, reader: Callable[[Path], str], errors: List[str]
) -> Tuple[int, ...]:
    try:
        return parse_cpu_list(reader(root / "online"))
    except Exception as error:  # Evidence collection must block, not fallback.
        errors.append(f"online CPU list is unavailable: {type(error).__name__}: {error}")
        return ()


def _affinity_cpu_ids(
    affinity_reader: Optional[Callable[[int], Iterable[int]]], errors: List[str]
) -> Tuple[int, ...]:
    if affinity_reader is None:
        errors.append("sched_getaffinity is unavailable")
        return ()
    try:
        values = tuple(affinity_reader(0))
        if not values or any(
            not isinstance(cpu, int) or isinstance(cpu, bool) or cpu < 0
            for cpu in values
        ):
            raise ValueError("affinity CPUs must be nonnegative integers")
        return tuple(sorted(set(values)))
    except Exception as error:
        errors.append(f"CPU affinity is unavailable: {type(error).__name__}: {error}")
        return ()


def _physical_core_ids(
    root: Path,
    online_cpu_ids: Iterable[int],
    reader: Callable[[Path], str],
    errors: List[str],
) -> Tuple[Tuple[int, int], ...]:
    physical = set()
    for cpu in online_cpu_ids:
        topology_root = root / f"cpu{cpu}" / "topology"
        try:
            package = _topology_identifier(
                reader(topology_root / "physical_package_id"),
                f"cpu{cpu} physical_package_id",
            )
            core = _topology_identifier(
                reader(topology_root / "core_id"), f"cpu{cpu} core_id"
            )
        except Exception as error:
            errors.append(f"cpu{cpu} topology is unavailable: {type(error).__name__}: {error}")
            continue
        physical.add((package, core))
    return tuple(sorted(physical))


def collect_linux_cpu_topology(
    sysfs_cpu_root: Union[str, Path] = "/sys/devices/system/cpu",
    *,
    read_text: Optional[Callable[[Path], str]] = None,
    sched_getaffinity: Optional[Callable[[int], Iterable[int]]] = None,
) -> LinuxCpuTopology:
    """Collect sysfs and scheduler facts without a logical-core fallback."""

    root = Path(sysfs_cpu_root)
    reader = read_text or (
        lambda path: path.read_text(encoding="utf-8", errors="strict")
    )
    errors: List[str] = []
    online_cpus = _online_cpu_ids(root, reader, errors)
    affinity_reader = sched_getaffinity or getattr(os, "sched_getaffinity", None)
    affinity_cpus = _affinity_cpu_ids(affinity_reader, errors)
    physical_core_ids = _physical_core_ids(root, online_cpus, reader, errors)
    return LinuxCpuTopology(
        online_cpu_ids=online_cpus,
        affinity_cpu_ids=affinity_cpus,
        physical_core_ids=physical_core_ids,
        full_host_affinity=bool(online_cpus)
        and affinity_cpus == online_cpus,
        errors=tuple(errors),
    )


def canonical_formal_threads(physical_core_count: int) -> Tuple[int, ...]:
    """Return the fixed formal scan plus the proven physical-core count."""

    if (
        not isinstance(physical_core_count, int)
        or isinstance(physical_core_count, bool)
        or physical_core_count <= 0
    ):
        raise ValueError("physical core count must be a positive integer")
    ordered: List[int] = []
    for value in (1, 2, 4, 8, 16, physical_core_count):
        if value not in ordered:
            ordered.append(value)
    return tuple(ordered)


def formal_host_blockers(
    topology: LinuxCpuTopology,
    environment: Mapping[str, str],
) -> List[str]:
    """Return every topology or runtime conflict that blocks formal evidence."""

    blockers = [f"formal CPU topology collection failed: {error}" for error in topology.errors]
    if not topology.online_cpu_ids:
        blockers.append("formal host online CPU set is missing")
    if not topology.affinity_cpu_ids:
        blockers.append("formal host process affinity CPU set is missing")
    elif (
        not topology.full_host_affinity
        or set(topology.affinity_cpu_ids) != set(topology.online_cpu_ids)
    ):
        blockers.append("formal host process affinity must equal the online CPU set")

    physical_core_count = topology.physical_core_count
    if physical_core_count is None:
        blockers.append("formal host package/core topology is incomplete")
    else:
        oversized = [
            thread
            for thread in canonical_formal_threads(physical_core_count)
            if thread > physical_core_count
        ]
        if oversized:
            blockers.append(
                "formal thread count "
                + str(max(oversized))
                + f" exceeds the proven {physical_core_count} physical cores"
            )

    for name in CONFLICTING_OPENMP_ENVIRONMENT:
        if name in environment:
            blockers.append(f"formal environment must not define conflicting {name}")
    return blockers


def sanitized_formal_environment(
    environment: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """Return a canonical formal subprocess environment without inherited pollution."""

    source = os.environ if environment is None else environment
    sanitized = {str(name): str(value) for name, value in source.items()}
    for name in FORMAL_ENVIRONMENT_POLLUTION:
        sanitized.pop(name, None)
    sanitized.update(CANONICAL_FORMAL_ENVIRONMENT)
    return sanitized
