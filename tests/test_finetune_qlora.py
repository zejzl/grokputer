"""Offline tests for the QLoRA training entry point: data contract and library arguments. No GPU, model or network."""
import json
from pathlib import Path

import pytest

from src.training import finetune_qlora as fq


def write_session(root: Path, name: str, data: dict, feedback: dict | None = None) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "session.json").write_text(json.dumps(data), encoding="utf-8")
    if feedback is not None:
        (directory / fq.FEEDBACK_FILE).write_text(json.dumps(feedback), encoding="utf-8")
    return directory


# The shape SessionLogger.save_metrics writes: top-level task and tool_executions, no rating.
def logger_session(task="open the settings"):
    return {
        "session_id": "x", "task": task, "duration_seconds": 3.0, "iterations": 2, "tool_executions": [
            {"tool": "screenshot", "params": {}, "result": "ok", "status": "success", "timestamp": 1.0},
            {"tool": "click", "params": {"x": 1, "y": 2}, "result": "miss", "status": "error", "timestamp": 2.0},
        ],
        "api_calls": [], "errors": [], "swarm_mode": False,
    }


def test_logger_shaped_session_without_feedback_is_not_training_data(tmp_path):
    write_session(tmp_path, "session_1", logger_session())
    assert fq.load_failed_sessions(fq.TrainingConfig(logs_dir=tmp_path)) == []


def test_feedback_sidecar_turns_a_logger_session_into_an_example(tmp_path):
    directory = write_session(tmp_path, "session_1", logger_session())
    fq.record_feedback(directory, 2, ["Wrong action selected"], "clicked the wrong icon")
    sessions = fq.load_failed_sessions(fq.TrainingConfig(logs_dir=tmp_path))
    assert len(sessions) == 1
    assert sessions[0]["actions"] == ["screenshot", "click"]
    examples = fq.generate_corrective_examples(sessions)
    assert len(examples) == 1
    assert examples[0]["instruction"] == "Complete this task: open the settings"
    assert "Wrong action selected" in examples[0]["input"]
    assert "clicked the wrong icon" in examples[0]["output"]


def test_high_rating_is_not_a_failure(tmp_path):
    directory = write_session(tmp_path, "session_1", logger_session())
    fq.record_feedback(directory, 5, ["nothing really"])
    assert fq.load_failed_sessions(fq.TrainingConfig(logs_dir=tmp_path)) == []


def test_legacy_metadata_layout_still_loads(tmp_path):
    legacy = {"metadata": {"task": "old task", "user_rating": 1, "what_went_wrong": ["Timeout"], "feedback_comment": ""},
              "iterations": [{"tool_results": [{"function_name": "click"}]}]}
    write_session(tmp_path, "session_old", legacy)
    sessions = fq.load_failed_sessions(fq.TrainingConfig(logs_dir=tmp_path))
    assert [s["task"] for s in sessions] == ["old task"]
    assert sessions[0]["actions"] == ["click"]


def test_corrupt_files_are_skipped(tmp_path):
    bad = tmp_path / "session_bad"
    bad.mkdir()
    (bad / "session.json").write_text("{not json", encoding="utf-8")
    assert fq.load_failed_sessions(fq.TrainingConfig(logs_dir=tmp_path)) == []


@pytest.mark.parametrize("rating,issues", [(0, ["x"]), (6, ["x"]), (True, ["x"]), (3, []), (3, [""])])
def test_record_feedback_rejects_bad_input(tmp_path, rating, issues):
    with pytest.raises(ValueError):
        fq.record_feedback(tmp_path, rating, issues)


def test_build_dataset_needs_enough_sessions(tmp_path):
    directory = write_session(tmp_path, "session_1", logger_session())
    fq.record_feedback(directory, 1, ["Timeout"])
    with pytest.raises(ValueError, match="record_feedback"):
        fq.build_dataset(fq.TrainingConfig(logs_dir=tmp_path))


def test_build_dataset_end_to_end(tmp_path):
    for i in range(5):
        fq.record_feedback(write_session(tmp_path, f"session_{i}", logger_session(f"task {i}")), 1, ["Timeout"])
    dataset = fq.build_dataset(fq.TrainingConfig(logs_dir=tmp_path))
    assert len(dataset) == 5
    assert set(dataset.column_names) == {"instruction", "input", "output"}


def test_training_arguments_construct_with_the_pinned_libraries(tmp_path):
    """The old keyword arguments (evaluation_strategy, tokenizer=, packing=, max_seq_length=) raise TypeError on trl 0.25."""
    config = fq.TrainingConfig(logs_dir=tmp_path, max_seq_length=512)
    args = fq.build_sft_config(config, tmp_path / "lora-v1")
    assert args.packing is True
    assert args.max_length == 512
    assert args.eval_strategy.value == "no"
    assert args.report_to == []


def test_sft_trainer_signature_matches_how_we_call_it():
    import inspect
    params = inspect.signature(fq.SFTTrainer.__init__).parameters
    for name in ("model", "args", "train_dataset", "processing_class", "formatting_func"):
        assert name in params


def test_importing_the_module_does_not_need_a_gpu():
    # Regression: the GPU check used to run at import and call exit(1), so nothing here could be tested without one.
    assert callable(fq.require_gpu)
