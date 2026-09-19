"""Самопроверка пайплайна на синтетическом эпизоде (сеть не нужна).

    python -m pytest src/tests -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config import Config  # noqa: E402
from src.kinematics import analyse_episode, phase_sequence  # noqa: E402
from src.language import decompose, parse_instruction, subtask_for_phase  # noqa: E402
from src.lerobot import LeRobotSource  # noqa: E402
from src.pipeline import run  # noqa: E402
from src.sources import prepare_lerobot_source  # noqa: E402
from src.validate import validate_file  # noqa: E402
from src.tests.make_fixture import build  # noqa: E402

EPISODES = 6


@pytest.fixture(scope="session")
def fixture_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("raw")
    build(root / "robot_demo", episodes=EPISODES, length=48, seed=0)
    return root


@pytest.fixture(scope="session")
def config() -> Config:
    return Config.load(ROOT / "config.yaml")


# ------------------------------------------------------------------- разбор
@pytest.mark.parametrize(
    ("text", "kind", "obj", "target"),
    [
        ("pick up the alphabet soup and place it in the basket", "pick_place", "alphabet soup", "basket"),
        ("put the cream cheese in the bowl", "pick_place", "cream cheese", "bowl"),
        ("open the middle drawer of the cabinet", "open", "middle drawer of the cabinet", ""),
        ("turn on the stove", "toggle", "stove", ""),
        ("move the blue block to the left of the red block", "push", "blue block", "red block"),
    ],
)
def test_instruction_parsing(text: str, kind: str, obj: str, target: str) -> None:
    parsed = parse_instruction(text)
    assert parsed.kind == kind
    assert parsed.obj_short == obj
    assert parsed.target_short == target
    steps = decompose(parsed)
    assert len(steps) >= 3
    assert subtask_for_phase(parsed, "grasp") in steps


# --------------------------------------------------------------- кинематика
def test_events_and_phases(fixture_root: Path, config: Config) -> None:
    source = LeRobotSource(fixture_root / "robot_demo", "robot_demo")
    state = prepare_lerobot_source(source, config)
    assert state.calibration is not None
    assert state.calibration.open_is_high is True

    found = {"grasp": 0, "release": 0, "slip": 0, "stall": 0}
    for episode in source.episodes():
        arrays = source.load_arrays(episode)
        assert arrays is not None
        kin = analyse_episode(
            arrays.state, arrays.action, state.schema, state.calibration,
            length=arrays.length, params=config.get("kinematics.events"),
        )
        found["grasp"] += len(kin.grasp_frames)
        found["release"] += len(kin.release_frames)
        found["slip"] += len(kin.slip_frames)
        found["stall"] += len(kin.stalls)
        phases = [name for name, _start, _end in phase_sequence(kin)]
        assert phases[0] == "approach"
        assert "grasp" in phases and "release" in phases

    # Захват и отпускание — в каждом эпизоде; срыв и застой — только в сценарных.
    assert found["grasp"] == EPISODES
    assert found["release"] == EPISODES
    assert found["slip"] == 1
    assert found["stall"] == 1


# ------------------------------------------------------------------ сквозной
@pytest.fixture(scope="session")
def generated(fixture_root: Path, config: Config, tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("out") / "annotations.jsonl"
    stats = run(fixture_root, out, config, num_workers=2)
    return {"path": out, "stats": stats}


def test_end_to_end_format(generated: dict) -> None:
    report = validate_file(generated["path"])
    assert report.ok, report.render()
    assert report.lines > 50


def test_task_coverage(generated: dict) -> None:
    tasks = set(generated["stats"]["train"]["by_task"])
    expected = {
        "gripper_state", "phase", "progress", "subtask", "instruction_check",
        "spatial_relation", "grounding_box", "grounding_point", "temporal_order",
        "frame_transition", "multiview_match", "view_role", "episode_summary",
        "failure_diagnosis", "recovery_instruction", "scene_caption",
    }
    missing = expected - tasks
    assert not missing, f"не сгенерированы типы задач: {sorted(missing)}"


def test_mcq_letters_are_balanced(generated: dict) -> None:
    letters = generated["stats"]["train"]["mcq_answer_letters"]
    assert letters, "нет примеров с множественным выбором"
    assert "?" not in letters
    total = sum(letters.values())
    assert max(letters.values()) / total < 0.6


def test_no_action_vector_leakage(generated: dict) -> None:
    """Датасет остаётся vision-language: сырые векторы действий в ответы не попадают."""
    banned = ("observation.state", "action:", "[-0.", "dx=", "action vector")
    with Path(generated["path"]).open(encoding="utf-8") as handle:
        for line in handle:
            answer = json.loads(line)["messages"][-1]["content"]
            assert not any(token in answer for token in banned), answer


def test_reproducible(fixture_root: Path, config: Config, tmp_path: Path) -> None:
    first = tmp_path / "a" / "annotations.jsonl"
    second = tmp_path / "b" / "annotations.jsonl"
    run(fixture_root, first, config, num_workers=1)
    run(fixture_root, second, config, num_workers=3)
    assert first.read_bytes() == second.read_bytes()


# ------------------------------------------------- видео-вариант LeRobot v3
#: Пара фикстуров с одинаковым сценарием: один в parquet, другой в mp4.
VIDEO_PAIR = {"episodes": 3, "length": 40, "seed": 0}


@pytest.fixture(scope="session")
def video_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("raw_video")
    build(root / "robot_video", video_backed=True, **VIDEO_PAIR)
    return root


@pytest.fixture(scope="session")
def video_twin_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("raw_twin")
    build(root / "robot_demo", video_backed=False, **VIDEO_PAIR)
    return root


def test_video_backed_frames_match_parquet(video_twin_root: Path, video_root: Path) -> None:
    """Кадр из mp4 берётся по метке времени эпизода и совпадает с parquet-вариантом."""
    import numpy as np

    from_parquet = LeRobotSource(video_twin_root / "robot_demo", "img")
    from_video = LeRobotSource(video_root / "robot_video", "vid")
    assert from_video.cameras[0].kind == "video"

    for episode_index in (0, 2):
        left_ep = from_parquet.episodes()[episode_index]
        right_ep = from_video.episodes()[episode_index]
        left_arrays = from_parquet.load_arrays(left_ep)
        right_arrays = from_video.load_arrays(right_ep)
        indices = [3, 17, 30]
        left = from_parquet.read_frames(left_ep, from_parquet.cameras[0], left_arrays, indices)
        right = from_video.read_frames(right_ep, from_video.cameras[0], right_arrays, indices)
        assert set(indices) <= set(right), "не все кадры декодированы из mp4"
        for index in indices:
            diff = np.abs(left[index].astype(int) - right[index].astype(int)).mean()
            assert diff < 8.0, f"кадр {index} эпизода {episode_index} разошёлся: {diff:.2f}"


def test_video_backed_pipeline(video_root: Path, config: Config, tmp_path: Path) -> None:
    out = tmp_path / "video" / "annotations.jsonl"
    stats = run(video_root, out, config, num_workers=1)
    assert stats["train"]["total"] > 0
    assert validate_file(out).ok
