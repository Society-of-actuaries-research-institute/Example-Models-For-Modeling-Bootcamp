"""JavaScript bridge used by the pywebview desktop UI."""

from __future__ import annotations

import getpass
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from mbc_model.data.models import ModelResults
from mbc_model.runner import run_with_results
from mbc_model.ui.preview import build_input_preview, build_output_preview


class DesktopBridge:
    """Small API object exposed to JavaScript by pywebview."""

    def __init__(
        self,
        project_root: Path | None = None,
        runner: Callable[[Path], Path | tuple[Path, ModelResults]] | None = None,
    ) -> None:
        self._project_root = (project_root or Path.cwd()).resolve()
        self._runner = runner
        self._window: Any = None
        self._lock = threading.Lock()
        self._started_at: float | None = None
        self._state: dict[str, Any] = {
            "status": "Ready",
            "running": False,
            "runtime": "00:00:00",
            "input_path": "",
            "output_path": "",
            "output": None,
            "error": "",
            "log": [],
        }

    def attach_window(self, window: Any) -> None:
        """Attach the pywebview window after creation."""
        self._window = window

    def browse_input_file(self) -> dict[str, Any]:
        """Open a native file picker and return an input workbook preview."""
        if self._window is None:
            return self._error("Desktop window is not ready.")

        try:
            import webview  # type: ignore[import-not-found]

            selected = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Excel workbooks (*.xlsm;*.xlsx)",),
            )
        except Exception as exc:  # pragma: no cover - exercised through pywebview
            return self._error(f"Could not open file picker: {exc}")

        if not selected:
            return {"ok": False, "cancelled": True}
        return self.get_input_preview(str(selected[0]))

    def get_input_preview(self, input_path: str) -> dict[str, Any]:
        """Return a bounded preview for a specific input workbook path."""
        path = self._resolve_path(input_path)
        if not path.exists():
            return self._error(f"Input file not found: {path}")

        try:
            preview = build_input_preview(path)
        except Exception as exc:
            return self._error(f"Could not read input workbook: {exc}")

        with self._lock:
            self._state["input_path"] = str(path)
            self._state["error"] = ""
            self._add_log_locked(f"Loaded workbook {path}", "Ready", input_path=str(path))
        return {"ok": True, "preview": preview, "status": self.get_run_status()}

    def start_run(self, input_path: str) -> dict[str, Any]:
        """Start a model run in the background."""
        path = self._resolve_path(input_path)
        if not path.exists():
            return self._error(f"Input file not found: {path}")

        with self._lock:
            if self._state["running"]:
                return self._error("A model run is already in progress.")

            self._started_at = time.perf_counter()
            self._state.update(
                {
                    "status": "Running",
                    "running": True,
                    "runtime": "00:00:00",
                    "input_path": str(path),
                    "output_path": "",
                    "output": None,
                    "error": "",
                }
            )
            self._add_log_locked(f"Started model run for {path}", "Running", input_path=str(path))

        thread = threading.Thread(target=self._run_model, args=(path,), daemon=True)
        thread.start()
        return {"ok": True, "status": self.get_run_status()}

    def get_run_status(self) -> dict[str, Any]:
        """Return the current run status."""
        with self._lock:
            state = dict(self._state)
            state["log"] = list(self._state["log"])
            if state["running"] and self._started_at is not None:
                state["runtime"] = _format_runtime(time.perf_counter() - self._started_at)
            return state

    def open_output_file(self, output_path: str | None = None) -> dict[str, Any]:
        """Open the generated output file using the OS default application."""
        path_text = output_path
        if not path_text:
            with self._lock:
                path_text = self._state.get("output_path")
        if not path_text:
            return self._error("No output file is available yet.")

        path = self._resolve_path(str(path_text))
        if not path.exists():
            return self._error(f"Output file not found: {path}")

        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys_platform() == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:  # pragma: no cover - platform shell behavior
            return self._error(f"Could not open output file: {exc}")

        with self._lock:
            self._add_log_locked(f"Opened output workbook {path}", "Opened", output_path=str(path))
        return {"ok": True}

    def _run_model(self, input_path: Path) -> None:
        try:
            if self._runner is not None:
                runner_result = self._runner(input_path)
                if isinstance(runner_result, tuple):
                    output_path, model_results = runner_result
                else:
                    output_path = runner_result
                    model_results = None
            else:
                output_path, model_results = run_with_results(
                    input_path, output_dir=self._project_root / "outputs", verbose=False
                )
            output_preview = build_output_preview(output_path, model_results)
        except Exception as exc:
            with self._lock:
                self._state.update(
                    {
                        "status": "Error",
                        "running": False,
                        "error": str(exc),
                        "runtime": _format_runtime(
                            time.perf_counter() - self._started_at
                            if self._started_at is not None
                            else 0
                        ),
                    }
                )
                self._add_log_locked(f"Run failed: {exc}", "Error", input_path=str(input_path))
            return

        with self._lock:
            runtime = time.perf_counter() - self._started_at if self._started_at is not None else 0
            self._state.update(
                {
                    "status": "Complete",
                    "running": False,
                    "runtime": _format_runtime(runtime),
                    "output_path": str(output_path),
                    "output": output_preview,
                    "error": "",
                }
            )
            self._add_log_locked(
                f"Wrote output workbook {output_path}",
                "Complete",
                input_path=str(input_path),
                output_path=str(output_path),
            )

    def _resolve_path(self, path_text: str) -> Path:
        path = Path(path_text)
        if not path.is_absolute():
            path = self._project_root / path
        return path.resolve()

    def _add_log_locked(
        self,
        action: str,
        status: str,
        input_path: str = "",
        output_path: str = "",
    ) -> None:
        now = datetime.now()
        self._state["log"].insert(
            0,
            {
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "user": getpass.getuser(),
                "action": action,
                "input_file": input_path,
                "output_file": output_path,
                "status": status,
            },
        )
        self._state["log"] = self._state["log"][:100]

    @staticmethod
    def _error(message: str) -> dict[str, Any]:
        return {"ok": False, "error": message}


def _format_runtime(seconds: float) -> str:
    total_seconds = int(round(seconds))
    return (
        f"{total_seconds // 3600:02d}:"
        f"{(total_seconds % 3600) // 60:02d}:"
        f"{total_seconds % 60:02d}"
    )


def sys_platform() -> str:
    """Small wrapper for tests."""
    import sys

    return sys.platform
