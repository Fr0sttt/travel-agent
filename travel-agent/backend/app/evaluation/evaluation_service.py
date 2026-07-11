"""任务完成后的异步评测服务。"""

from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.evaluation_runner import EvaluationRunner


class EvaluationService:
    """提交、执行、持久化评测任务，并为后续自进化保留失败样本。"""

    def __init__(self, storage_dir: str | Path | None = None, status_callback: Any | None = None) -> None:
        self.storage_dir = Path(storage_dir or Path(__file__).resolve().parents[1] / "runtime" / "evaluations")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.runner = EvaluationRunner()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.tasks: set[asyncio.Task[Any]] = set()
        self.status_callback = status_callback

    def submit(self, session_data: dict[str, Any]) -> str:
        """提交后台任务，立即返回评测运行 ID。"""
        session_id = session_data.get("session_id", "unknown")
        existing = self.get_latest_for_session(session_id)
        if existing:
            # 一个会话默认对应一次规划，重复请求不重复触发评测。
            return str(existing["run_id"])
        run_id = f"eval_{uuid.uuid4().hex[:12]}"
        job = {
            "run_id": run_id,
            "session_id": session_id,
            "trace_id": session_data.get("trace_id"),
            "status": "queued",
            "created_at": datetime.now().isoformat(),
        }
        self.jobs[run_id] = job
        # 任务提交后立即落盘，避免进程重启或查询落到其他 worker 时丢失 queued 状态。
        self._write_job(job)
        self._schedule_status_notification(job)
        task = asyncio.create_task(self._run(run_id, session_data))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return run_id

    async def _run(self, run_id: str, session_data: dict[str, Any]) -> None:
        job = self.jobs[run_id]
        job["status"] = "running"
        job["started_at"] = datetime.now().isoformat()
        self._write_job(job)
        await self._notify_status(job)
        try:
            report = await self.runner.run_full_evaluation(session_data)
            report_data = report.to_dict()
            report_data["run_id"] = run_id
            report_data["trace_id"] = session_data.get("trace_id")
            self._write_json(run_id, report_data)
            if self._is_failure(report_data):
                self._append_failure(report_data, session_data)
            self._publish_scores(report_data)
            job.update({"status": "completed", "report": report_data, "finished_at": datetime.now().isoformat()})
            self._write_job(job)
            await self._notify_status(job)
        except Exception as exc:
            error = {"run_id": run_id, "session_id": session_data.get("session_id"), "error": str(exc)}
            job.update({"status": "failed", "error": str(exc), "finished_at": datetime.now().isoformat()})
            self._write_job(job)
            await self._notify_status(job)

    def _schedule_status_notification(self, job: dict[str, Any]) -> None:
        if self.status_callback is None:
            return
        task = asyncio.create_task(self._notify_status(job))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def _notify_status(self, job: dict[str, Any]) -> None:
        if self.status_callback is None:
            return
        try:
            result = self.status_callback(job)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            print(f"[EvaluationService] 评测状态回写失败 run_id={job.get('run_id')}: {exc}", flush=True)

    def _is_failure(self, report: dict[str, Any]) -> bool:
        if report.get("overall_score", 0) < 0.6:
            return True
        return any(not item.get("passed", False) for item in report.get("results", []))

    def _write_json(self, run_id: str, data: dict[str, Any]) -> None:
        path = self.storage_dir / f"{run_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _write_job(self, job: dict[str, Any]) -> None:
        """把任务状态和报告作为一个原子语义对象保存，查询时不会只拿到旧报告。"""
        self._write_json(str(job["run_id"]), job)

    def _read_job_file(self, run_id: str) -> dict[str, Any] | None:
        path = self.storage_dir / f"{run_id}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        # 兼容改造前只保存 EvalReport 的文件。
        if "status" not in payload and "overall_score" in payload:
            return {
                "run_id": run_id,
                "session_id": payload.get("session_id", "unknown"),
                "trace_id": payload.get("trace_id"),
                "status": "completed",
                "created_at": payload.get("timestamp"),
                "finished_at": payload.get("timestamp"),
                "report": payload,
            }
        return payload

    def _append_failure(self, report: dict[str, Any], session_data: dict[str, Any]) -> None:
        item = {
            "recorded_at": datetime.now().isoformat(),
            "session_id": session_data.get("session_id"),
            "trace_id": session_data.get("trace_id"),
            "run_id": report.get("run_id"),
            "user_request": session_data.get("user_request", ""),
            "report": report,
            "trajectory": session_data.get("trajectory", []),
            "tool_calls": session_data.get("tool_calls", []),
            "next_action": "等待后台自进化 Agent 归因并生成回归用例",
        }
        with (self.storage_dir / "failures.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _publish_scores(report: dict[str, Any]) -> None:
        """将评测维度回写到同一条 Langfuse Trace。"""
        trace_id = report.get("trace_id")
        if not trace_id:
            return
        try:
            from observability.langfuse_client import get_langfuse
            client = get_langfuse()
            for name, value in report.get("dimension_scores", {}).items():
                client.add_score(trace_id, f"eval_{name}", float(value), report.get("recommendations", [""])[0])
            client.add_score(trace_id, "eval_overall", float(report.get("overall_score", 0)))
        except Exception:
            pass

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self.jobs.get(run_id) or self._read_job_file(run_id)

    def get_latest_for_session(self, session_id: str) -> dict[str, Any] | None:
        candidates = [j for j in self.jobs.values() if j.get("session_id") == session_id]
        known_ids = {str(item.get("run_id")) for item in candidates}
        for path in self.storage_dir.glob("eval_*.json"):
            run_id = path.stem
            if run_id in known_ids:
                continue
            job = self._read_job_file(run_id)
            if job and job.get("session_id") == session_id:
                candidates.append(job)
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.get("created_at", ""))

    async def shutdown(self) -> None:
        """应用关闭时给后台评测一个短暂的收尾窗口。"""
        if self.tasks:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)
