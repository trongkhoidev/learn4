from datetime import date

import pytest

from scripts.asr_training.evaluate_asr import evaluate
from scripts.asr_training.prepare_manifest import training_inputs, validate_rows
from scripts.asr_training.train_whisper_lora import training_rows as lora_training_rows


def _manifest_row(sample, speaker, split="train"):
    return {
        "sample_id": sample,
        "speaker_id": speaker,
        "session_id": f"session-{speaker}",
        "split": split,
        "part": 1,
        "question_id": "q1",
        "audio_path": f"audio/{sample}.wav",
        "reference_verbatim": "Yesterday I go to the park.",
        "reference_corrected_for_coaching": "Yesterday I went to the park.",
        "human_unclear_spans": [],
        "annotation_version": "verbatim-v1",
        "consent_id": f"consent-{speaker}",
        "retention_until": "2027-01-01",
        "metadata": {"device": "phone", "region": "south", "noise": "quiet", "accent": "vi"},
    }


def test_training_export_contains_only_verbatim_inputs():
    rows = [_manifest_row("s1", "p1"), _manifest_row("s2", "p2", "test")]
    assert validate_rows(rows, as_of=date(2026, 10, 18)) == []
    exported = training_inputs(rows)
    assert exported == [{
        "sample_id": "s1", "audio_path": "audio/s1.wav", "text": "Yesterday I go to the park.",
    }]
    assert "went" not in exported[0]["text"]


def test_manifest_rejects_speaker_and_session_leakage():
    rows = [_manifest_row("s1", "p1", "train"), _manifest_row("s2", "p1", "test")]
    errors = validate_rows(rows, as_of=date(2026, 10, 18))
    assert any("speaker_id" in error and "multiple splits" in error for error in errors)


def test_lora_training_rows_require_real_audio_and_both_splits(tmp_path):
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "s1.wav").write_bytes(b"wav")
    (tmp_path / "audio" / "s2.wav").write_bytes(b"wav")
    rows = [_manifest_row("s1", "p1"), _manifest_row("s2", "p2", "validation")]
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("".join(__import__("json").dumps(row) + "\n" for row in rows))
    exported = lora_training_rows(manifest, min_train=1, min_validation=1)
    assert exported["train"][0]["text"] == "Yesterday I go to the park."
    assert exported["validation"][0]["sample_id"] == "s2"

    (tmp_path / "audio" / "s2.wav").unlink()
    with pytest.raises(ValueError, match="audio files are missing"):
        lora_training_rows(manifest, min_train=1, min_validation=1)


def test_asr_evaluator_reports_error_preservation_silence_slices_and_speaker_ci():
    rows = [
        {
            "sample_id": "a1", "speaker_id": "p1", "session_id": "m1", "split": "test",
            "part": 1, "reference_verbatim": "I go yesterday um I go", "prediction": "I go yesterday I",
            "has_speech": True,
            "preservation_tags": {"grammar_errors": ["I go yesterday"], "fillers": ["um"], "repetitions": ["I go"]},
            "metadata": {"accent": "vi", "device": "phone", "noise": "quiet", "region": "south"},
        },
        {
            "sample_id": "a2", "speaker_id": "p2", "session_id": "m2", "split": "test",
            "part": 2, "reference_verbatim": "", "prediction": "hello there", "has_speech": False,
            "preservation_tags": {},
            "metadata": {"accent": "vi", "device": "desktop", "noise": "quiet", "region": "north"},
        },
    ]
    report = evaluate(rows, bootstrap_samples=50, seed=4)
    assert report["sample_count"] == 2
    assert report["speaker_count"] == 2
    assert report["preservation"]["grammar_errors"]["rate"] == 1.0
    assert report["preservation"]["fillers"]["rate"] == 0.0
    assert report["preservation"]["repetitions"]["rate"] == 1.0
    assert report["silence"] == {"n": 1, "hallucinated": 1, "rate": 1.0}
    assert report["bootstrap_by_speaker"]["wer_raw"]["wer_95_ci"] is not None
    assert "accent=vi" in report["slices"]
    assert report["proposed_asr_gates"]["gates_are_proposals_not_certification"] is True


def test_evaluator_rejects_cross_split_speaker_leakage():
    rows = [
        {"sample_id": "a1", "speaker_id": "p1", "session_id": "m1", "split": "train"},
        {"sample_id": "a2", "speaker_id": "p1", "session_id": "m2", "split": "test"},
    ]
    with pytest.raises(ValueError, match="speaker_id.*leaks across splits"):
        evaluate(rows, bootstrap_samples=0)
