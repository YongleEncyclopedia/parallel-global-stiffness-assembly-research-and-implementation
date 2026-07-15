#!/usr/bin/env python3
"""Contract tests for Linux formal-host topology and environment handling."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Dict, Iterable, Optional


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "formal_host.py"


class FormalHostContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SCRIPT.is_file(), f"formal-host module is missing: {SCRIPT}")
        spec = importlib.util.spec_from_file_location("csc3_formal_host_test", SCRIPT)
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.host = module
        self.sysfs_root = Path("/injected/sys/devices/system/cpu")

    def collect_topology(
        self,
        physical_cores: int,
        *,
        threads_per_core: int = 2,
        affinity: Optional[Iterable[int]] = None,
        omit: Optional[Path] = None,
    ):
        logical_cpus = physical_cores * threads_per_core
        online = tuple(range(logical_cpus))
        files: Dict[Path, str] = {
            self.sysfs_root / "online": f"0-{logical_cpus - 1}\n"
        }
        for cpu in online:
            core = cpu // threads_per_core
            topology_root = self.sysfs_root / f"cpu{cpu}" / "topology"
            files[topology_root / "physical_package_id"] = f"{core // 8}\n"
            files[topology_root / "core_id"] = f"{core % 8}\n"
        if omit is not None:
            files.pop(omit)

        def read_text(path: Path) -> str:
            try:
                return files[Path(path)]
            except KeyError as error:
                raise FileNotFoundError(path) from error

        allowed = set(online if affinity is None else affinity)
        return self.host.collect_linux_cpu_topology(
            self.sysfs_root,
            read_text=read_text,
            sched_getaffinity=lambda _pid: allowed,
        )

    def test_parse_cpu_list_expands_ranges_sorts_and_deduplicates(self) -> None:
        self.assertEqual(
            self.host.parse_cpu_list("8,0-3,2,10-11\n"),
            (0, 1, 2, 3, 8, 10, 11),
        )

    def test_parse_cpu_list_rejects_malformed_or_reversed_ranges(self) -> None:
        for value in ("", "0-", "3-1", "0,,2", "-1", "cpu0"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.host.parse_cpu_list(value)

    def test_collects_online_affinity_and_package_core_topology(self) -> None:
        topology = self.collect_topology(16)

        self.assertEqual(topology.online_cpu_ids, tuple(range(32)))
        self.assertEqual(topology.affinity_cpu_ids, tuple(range(32)))
        self.assertEqual(
            topology.physical_core_ids,
            tuple((package, core) for package in range(2) for core in range(8)),
        )
        self.assertTrue(topology.full_host_affinity)
        self.assertEqual(topology.logical_cpu_count, 32)
        self.assertEqual(topology.physical_core_count, 16)
        self.assertTrue(topology.topology_complete)
        self.assertEqual(topology.errors, ())

    def test_canonical_threads_cover_32_16_12_and_8_physical_cores(self) -> None:
        expected = {
            32: (1, 2, 4, 8, 16, 32),
            16: (1, 2, 4, 8, 16),
            12: (1, 2, 4, 8, 16, 12),
            8: (1, 2, 4, 8, 16),
        }
        for physical_cores, threads in expected.items():
            with self.subTest(physical_cores=physical_cores):
                self.assertEqual(
                    self.host.canonical_formal_threads(physical_cores), threads
                )

    def test_invalid_physical_core_counts_do_not_create_thread_contracts(self) -> None:
        for value in (0, -1, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.host.canonical_formal_threads(value)

    def test_valid_16_core_unrestricted_host_has_no_blockers(self) -> None:
        topology = self.collect_topology(16)
        self.assertEqual(self.host.formal_host_blockers(topology, {}), [])

    def test_hosts_below_16_physical_cores_are_blocked(self) -> None:
        for physical_cores in (12, 8):
            with self.subTest(physical_cores=physical_cores):
                blockers = self.host.formal_host_blockers(
                    self.collect_topology(physical_cores), {}
                )
                self.assertTrue(any("16" in blocker for blocker in blockers))

    def test_same_count_different_affinity_set_is_blocked(self) -> None:
        topology = self.collect_topology(16, affinity=range(32, 64))
        blockers = self.host.formal_host_blockers(topology, {})
        self.assertTrue(any("affinity" in blocker for blocker in blockers))

    def test_forged_full_host_affinity_boolean_cannot_hide_set_mismatch(self) -> None:
        original = self.collect_topology(16)
        topology = self.host.LinuxCpuTopology(
            online_cpu_ids=original.online_cpu_ids,
            affinity_cpu_ids=tuple(range(32, 64)),
            physical_core_ids=original.physical_core_ids,
            full_host_affinity=True,
        )
        blockers = self.host.formal_host_blockers(topology, {})
        self.assertTrue(any("affinity" in blocker for blocker in blockers))

    def test_missing_online_topology_is_not_replaced_by_logical_count(self) -> None:
        def missing(_path: Path) -> str:
            raise FileNotFoundError("missing sysfs")

        topology = self.host.collect_linux_cpu_topology(
            self.sysfs_root,
            read_text=missing,
            sched_getaffinity=lambda _pid: set(range(32)),
        )

        self.assertEqual(topology.online_cpu_ids, ())
        self.assertIsNone(topology.physical_core_count)
        self.assertFalse(topology.topology_complete)
        self.assertTrue(topology.errors)
        self.assertTrue(self.host.formal_host_blockers(topology, {}))

    def test_incomplete_per_cpu_topology_has_no_physical_fallback(self) -> None:
        missing = self.sysfs_root / "cpu31" / "topology" / "core_id"
        topology = self.collect_topology(16, omit=missing)

        self.assertEqual(topology.logical_cpu_count, 32)
        self.assertIsNone(topology.physical_core_count)
        self.assertFalse(topology.topology_complete)
        self.assertTrue(any("cpu31" in error for error in topology.errors))
        self.assertTrue(
            any(
                "topology" in blocker
                for blocker in self.host.formal_host_blockers(topology, {})
            )
        )

    def test_conflicting_openmp_runtime_limits_are_blockers(self) -> None:
        topology = self.collect_topology(16)
        conflicts = {
            "OMP_NUM_THREADS": "8",
            "OMP_THREAD_LIMIT": "8",
            "GOMP_CPU_AFFINITY": "0-7",
            "KMP_AFFINITY": "compact",
        }
        for name, value in conflicts.items():
            with self.subTest(name=name):
                blockers = self.host.formal_host_blockers(topology, {name: value})
                self.assertTrue(any(name in blocker for blocker in blockers))

    def test_sanitized_environment_is_canonical_and_removes_pollution(self) -> None:
        polluted = {
            "PATH": "/usr/bin",
            "LC_ALL": "zh_CN.UTF-8",
            "TZ": "Asia/Shanghai",
            "CC": "clang",
            "CXX": "clang++",
            "OMP_DYNAMIC": "true",
            "OMP_PROC_BIND": "spread",
            "OMP_PLACES": "threads",
            "OMP_NUM_THREADS": "99",
            "OMP_THREAD_LIMIT": "8",
            "GOMP_CPU_AFFINITY": "0-7",
            "KMP_AFFINITY": "compact",
            "PYTHONOPTIMIZE": "2",
            "PYTHONPATH": "/tmp/injected",
            "PYTHONHOME": "/tmp/python",
        }
        original = dict(polluted)

        sanitized = self.host.sanitized_formal_environment(polluted)

        self.assertEqual(polluted, original)
        self.assertEqual(sanitized["PATH"], "/usr/bin")
        self.assertEqual(sanitized["LC_ALL"], "C")
        self.assertEqual(sanitized["TZ"], "UTC")
        self.assertEqual(sanitized["CC"], "/usr/bin/gcc")
        self.assertEqual(sanitized["CXX"], "/usr/bin/g++")
        self.assertEqual(sanitized["OMP_DYNAMIC"], "false")
        self.assertEqual(sanitized["OMP_PROC_BIND"], "close")
        self.assertEqual(sanitized["OMP_PLACES"], "cores")
        for name in (
            "OMP_NUM_THREADS",
            "OMP_THREAD_LIMIT",
            "GOMP_CPU_AFFINITY",
            "KMP_AFFINITY",
            "PYTHONOPTIMIZE",
            "PYTHONPATH",
            "PYTHONHOME",
        ):
            self.assertNotIn(name, sanitized)


if __name__ == "__main__":
    unittest.main()
