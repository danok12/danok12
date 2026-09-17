"""Оркестрация: источники → эпизоды → примеры → сбалансированный ShareGPT JSONL."""

from __future__ import annotations

import multiprocessing as mp
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .frames import stable_subsample
from .lerobot import EpisodeMeta, LeRobotSource
from .records import Sample
from .sources import (
    SourceSpec,
    SourceState,
    _iter_videos,
    prepare_lerobot_source,
    process_lerobot_episode,
    process_video_episode,
    resolve_sources,
)
from .utils import chunked, get_logger
from .writer import balance, deduplicate, write_outputs

LOGGER = get_logger(__name__)

_WORKER: dict[str, Any] = {}


@dataclass
class Job:
    source_name: str
    source_path: str
    kind: str
    episodes: list[EpisodeMeta] | list[str]


def _worker_init(config_data: dict[str, Any], out_root: str, dry_run: bool, states: dict[str, SourceState]) -> None:
    _WORKER["config"] = Config(config_data)
    _WORKER["out_root"] = Path(out_root)
    _WORKER["dry_run"] = dry_run
    _WORKER["states"] = states
    _WORKER["sources"] = {}


def _get_source(name: str, path: str) -> LeRobotSource:
    cache = _WORKER.setdefault("sources", {})
    if name not in cache:
        cache[name] = LeRobotSource(Path(path), name)
    return cache[name]


def _run_job(job: Job) -> list[Sample]:
    cfg: Config = _WORKER["config"]
    out_root: Path = _WORKER["out_root"]
    dry_run: bool = _WORKER["dry_run"]
    out: list[Sample] = []
    if job.kind == "lerobot":
        source = _get_source(job.source_name, job.source_path)
        state = _WORKER["states"][job.source_name]
        for episode in job.episodes:  # type: ignore[assignment]
            try:
                out.extend(process_lerobot_episode(source, state, episode, cfg, out_root, dry_run))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("эпизод %s пропущен: %s", getattr(episode, "uid", "?"), exc)
    else:
        for video in job.episodes:  # type: ignore[assignment]
            try:
                out.extend(process_video_episode(Path(str(video)), job.source_name, cfg, out_root, dry_run))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("видео %s пропущено: %s", video, exc)
    return out


def _build_jobs(
    specs: list[SourceSpec],
    cfg: Config,
    limit_episodes: int | None,
) -> tuple[list[Job], dict[str, SourceState], dict[str, Any]]:
    jobs: list[Job] = []
    states: dict[str, SourceState] = {}
    summary: dict[str, Any] = {}
    chunk = int(cfg.get("runtime.chunk_episodes", 8))
    per_source_limit = cfg.get("budget.max_episodes_per_source")
    per_source_limit = int(per_source_limit) if per_source_limit else None
    if limit_episodes:
        per_source_limit = min(per_source_limit or limit_episodes, limit_episodes)

    for spec in specs:
        if spec.kind == "lerobot":
            source = LeRobotSource(spec.path, spec.name)
            episodes = source.episodes()
            if not episodes:
                LOGGER.warning("%s: эпизоды не найдены", spec.name)
                continue
            states[spec.name] = prepare_lerobot_source(source, cfg)
            selected = stable_subsample(episodes, per_source_limit, cfg.seed, f"{spec.name}:episodes")
            summary[spec.name] = {
                "kind": "lerobot",
                "path": str(spec.path),
                "episodes_total": len(episodes),
                "episodes_used": len(selected),
                "cameras": [c.name for c in source.cameras],
                "fps": source.fps,
                "gripper_calibrated": states[spec.name].calibration is not None,
            }
            for batch in chunked(selected, chunk):
                jobs.append(Job(spec.name, str(spec.path), "lerobot", batch))
        else:
            extensions = tuple(str(x).lower() for x in (cfg.get("input.video_extensions") or []))
            videos = [str(p) for p in _iter_videos(spec.path, extensions)]
            videos = stable_subsample(videos, per_source_limit, cfg.seed, f"{spec.name}:videos")
            if not videos:
                continue
            summary[spec.name] = {
                "kind": "video_folder",
                "path": str(spec.path),
                "videos_used": len(videos),
            }
            for batch in chunked(videos, max(1, chunk // 2)):
                jobs.append(Job(spec.name, str(spec.path), "video_folder", batch))
    return jobs, states, summary


def run(
    input_root: Path,
    output: Path,
    cfg: Config,
    *,
    limit_episodes: int | None = None,
    dry_run: bool = False,
    num_workers: int | None = None,
) -> dict[str, Any]:
    started = time.time()
    input_root = Path(input_root).resolve()
    output = Path(output).resolve()
    out_root = output.parent
    out_root.mkdir(parents=True, exist_ok=True)

    specs = resolve_sources(input_root, cfg)
    if not specs:
        raise SystemExit(
            f"В {input_root} не найдено ни одного источника: ожидается каталог LeRobot v3 "
            "(meta/info.json) или каталог с видеофайлами. Явные источники задаются в config.yaml."
        )
    LOGGER.info("источники: %s", ", ".join(f"{s.name}({s.kind})" for s in specs))

    jobs, states, summary = _build_jobs(specs, cfg, limit_episodes)
    if not jobs:
        raise SystemExit("Нет задач для обработки: проверьте пути и budget.max_episodes_per_source")

    workers = num_workers if num_workers is not None else int(cfg.get("runtime.num_workers", 0))
    if workers <= 0:
        workers = min(16, max(1, (os.cpu_count() or 2)))
    workers = max(1, min(workers, len(jobs)))
    LOGGER.info("эпизодных задач: %d, воркеров: %d", len(jobs), workers)

    collected: list[Sample] = []
    if workers == 1:
        _worker_init(cfg.to_dict(), str(out_root), dry_run, states)
        for done, job in enumerate(jobs, 1):
            collected.extend(_run_job(job))
            _log_progress(cfg, done, len(jobs), len(collected))
    else:
        context = mp.get_context("spawn" if os.name == "nt" else "fork")
        with context.Pool(
            processes=workers,
            initializer=_worker_init,
            initargs=(cfg.to_dict(), str(out_root), dry_run, states),
        ) as pool:
            for done, result in enumerate(pool.imap_unordered(_run_job, jobs, chunksize=1), 1):
                collected.extend(result)
                _log_progress(cfg, done, len(jobs), len(collected))

    LOGGER.info("собрано примеров: %d", len(collected))
    unique = deduplicate(collected)
    selected, report = balance(unique, cfg)
    extra = {
        "sources": summary,
        "selection": report,
        "duplicates_removed": len(collected) - len(unique),
        "input_root": str(input_root),
        "elapsed_sec": round(time.time() - started, 1),
        "dry_run": dry_run,
    }
    if dry_run:
        LOGGER.info("dry-run: файлы не записаны, отобрано %d примеров", len(selected))
        from .writer import build_stats, split_train_val

        train, val = split_train_val(selected, cfg)
        return build_stats(train, val, cfg, extra)
    stats = write_outputs(selected, output, cfg, extra)
    LOGGER.info("готово за %.1f c", time.time() - started)
    return stats


def _log_progress(cfg: Config, done: int, total: int, collected: int) -> None:
    if not bool(cfg.get("runtime.progress", True)):
        return
    step = max(1, total // 20)
    if done % step == 0 or done == total:
        LOGGER.info("обработано %d/%d задач, примеров: %d", done, total, collected)
