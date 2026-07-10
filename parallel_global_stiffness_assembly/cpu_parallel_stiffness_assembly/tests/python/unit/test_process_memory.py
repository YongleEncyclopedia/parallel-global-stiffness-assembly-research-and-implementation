from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


CPU_ROOT = Path(__file__).resolve().parents[3]
HELPER_PATH = CPU_ROOT / "scripts" / "process_memory.py"


def load_helper() -> ModuleType:
    if not HELPER_PATH.is_file():
        raise AssertionError(f"missing process memory helper: {HELPER_PATH}")
    spec = importlib.util.spec_from_file_location("process_memory", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load process memory helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def child_command(returncode: int) -> list[str]:
    return [
        sys.executable,
        "-c",
        f"import time; time.sleep(0.05); raise SystemExit({returncode})",
    ]


class FakeProcess:
    def __init__(
        self,
        *,
        poll_result: int | None,
        wait_effects: list[int | BaseException],
    ) -> None:
        self.pid = 1234
        self.returncode: int | None = None
        self.poll_result = poll_result
        self.wait_effects = list(wait_effects)
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls: list[float | None] = []

    def poll(self) -> int | None:
        return self.poll_result

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if not self.wait_effects:
            raise AssertionError("unexpected process.wait call")
        effect = self.wait_effects.pop(0)
        if isinstance(effect, BaseException):
            raise effect
        self.returncode = effect
        return effect


class StrictTextStream:
    def __init__(self, encoding: str) -> None:
        self.encoding = encoding
        self.writes: list[str] = []

    def write(self, text: str) -> int:
        text.encode(self.encoding, errors="strict")
        self.writes.append(text)
        return len(text)


class ProcessMemoryTests(unittest.TestCase):
    def test_write_captured_text_preserves_utf8(self) -> None:
        helper = load_helper()
        writer = getattr(helper, "write_captured_text", None)
        self.assertIsNotNone(writer)
        stream = StrictTextStream("utf-8")

        writer(stream, "assembled 刚度\n")

        self.assertEqual(stream.writes, ["assembled 刚度\n"])

    def test_write_captured_text_escapes_chinese_for_cp1252(self) -> None:
        helper = load_helper()
        writer = getattr(helper, "write_captured_text", None)
        self.assertIsNotNone(writer)
        stream = StrictTextStream("cp1252")

        writer(stream, "assembled 刚度\n")

        self.assertEqual(stream.writes, [r"assembled \u521a\u5ea6" + "\n"])

    def test_successful_child_returns_zero(self) -> None:
        helper = load_helper()

        returncode, payload = helper.run_child_with_memory(child_command(0))

        self.assertEqual(returncode, 0)
        self.assertGreater(float(payload["peak_rss_mb"]), 0.0)

    def test_nonzero_child_returncode_is_preserved(self) -> None:
        helper = load_helper()

        returncode, _ = helper.run_child_with_memory(child_command(7))

        self.assertEqual(returncode, 7)

    def test_payload_schema_identifies_platform_measurement(self) -> None:
        helper = load_helper()

        _, payload = helper.run_child_with_memory(child_command(0))

        self.assertEqual(
            set(payload),
            {
                "peak_rss_mb",
                "memory_metric",
                "measurement_source",
                "peak_working_set_mb",
                "peak_private_bytes_mb",
            },
        )
        if sys.platform == "win32":
            self.assertEqual(payload["memory_metric"], "windows_peak_working_set")
            self.assertEqual(
                payload["measurement_source"],
                "GetProcessMemoryInfo.PeakWorkingSetSize",
            )
            self.assertGreater(float(payload["peak_working_set_mb"]), 0.0)
            self.assertGreater(float(payload["peak_private_bytes_mb"]), 0.0)
        else:
            self.assertEqual(payload["memory_metric"], "process_ru_maxrss")
            self.assertEqual(
                payload["measurement_source"],
                "resource.getrusage(RUSAGE_CHILDREN).ru_maxrss",
            )
            self.assertEqual(payload["peak_working_set_mb"], "")
            self.assertEqual(payload["peak_private_bytes_mb"], "")

    def test_open_failure_reaps_child_that_already_exited(self) -> None:
        helper = load_helper()
        process = FakeProcess(poll_result=5, wait_effects=[5])

        with (
            mock.patch.object(helper.subprocess, "Popen", return_value=process),
            mock.patch.object(
                helper,
                "_open_windows_process",
                side_effect=RuntimeError("open failed"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "open failed"):
                helper._run_windows_child(["child"])

        self.assertEqual(process.terminate_calls, 0)
        self.assertEqual(process.kill_calls, 0)
        self.assertEqual(process.wait_calls, [None])

    def test_query_failure_terminates_then_kills_and_reaps_on_timeout(self) -> None:
        helper = load_helper()
        timeout = subprocess.TimeoutExpired(cmd=["child"], timeout=1.0)
        process = FakeProcess(poll_result=None, wait_effects=[timeout, 9])
        kernel32 = mock.Mock()
        kernel32.CloseHandle.return_value = 0

        with (
            mock.patch.object(helper.subprocess, "Popen", return_value=process),
            mock.patch.object(helper, "_open_windows_process", return_value=88),
            mock.patch.object(
                helper,
                "_query_windows_process_memory",
                side_effect=ValueError("query failed"),
            ),
            mock.patch.object(helper, "kernel32", kernel32, create=True),
            mock.patch.object(
                helper,
                "_last_windows_error",
                return_value=RuntimeError("close failed"),
            ) as last_error,
        ):
            with self.assertRaisesRegex(ValueError, "query failed"):
                helper._run_windows_child(["child"])

        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.kill_calls, 1)
        self.assertEqual(len(process.wait_calls), 2)
        self.assertIsNotNone(process.wait_calls[0])
        self.assertGreater(float(process.wait_calls[0]), 0.0)
        self.assertIsNone(process.wait_calls[1])
        kernel32.CloseHandle.assert_called_once_with(88)
        last_error.assert_not_called()

    def test_normal_windows_path_waits_and_reaps_child(self) -> None:
        helper = load_helper()
        process = FakeProcess(poll_result=0, wait_effects=[0])
        kernel32 = mock.Mock()
        kernel32.CloseHandle.return_value = 1
        memory = {
            "working_set_mb": 1.0,
            "peak_working_set_mb": 2.0,
            "private_bytes_mb": 3.0,
            "peak_private_bytes_mb": 4.0,
        }

        with (
            mock.patch.object(helper.subprocess, "Popen", return_value=process),
            mock.patch.object(helper, "_open_windows_process", return_value=99),
            mock.patch.object(
                helper,
                "_query_windows_process_memory",
                return_value=memory,
            ),
            mock.patch.object(helper, "kernel32", kernel32, create=True),
        ):
            returncode, payload = helper._run_windows_child(["child"])

        self.assertEqual(returncode, 0)
        self.assertEqual(payload["peak_rss_mb"], 2.0)
        self.assertEqual(payload["peak_private_bytes_mb"], 4.0)
        self.assertEqual(process.wait_calls, [None])
        self.assertEqual(process.terminate_calls, 0)
        self.assertEqual(process.kill_calls, 0)
        kernel32.CloseHandle.assert_called_once_with(99)

    def test_close_failure_propagates_when_it_is_the_only_failure(self) -> None:
        helper = load_helper()
        process = FakeProcess(poll_result=0, wait_effects=[0])
        kernel32 = mock.Mock()
        kernel32.CloseHandle.return_value = 0
        memory = {
            "working_set_mb": 1.0,
            "peak_working_set_mb": 2.0,
            "private_bytes_mb": 3.0,
            "peak_private_bytes_mb": 4.0,
        }

        with (
            mock.patch.object(helper.subprocess, "Popen", return_value=process),
            mock.patch.object(helper, "_open_windows_process", return_value=99),
            mock.patch.object(
                helper,
                "_query_windows_process_memory",
                return_value=memory,
            ),
            mock.patch.object(helper, "kernel32", kernel32, create=True),
            mock.patch.object(
                helper,
                "_last_windows_error",
                return_value=RuntimeError("close failed"),
            ) as last_error,
        ):
            with self.assertRaisesRegex(RuntimeError, "close failed"):
                helper._run_windows_child(["child"])

        self.assertEqual(process.wait_calls, [None])
        last_error.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
