from app.modules.speaking.assessment.quality import build_assessment_quality


def _criteria(pronunciation=None):
    return {
        "fluency_coherence": {"band": 6.5},
        "lexical_resource": {"band": 6.0},
        "grammatical_range_accuracy": {"band": 6.0},
        "pronunciation": {"band": pronunciation},
    }


def test_quality_exposes_language_only_scope_without_fake_pronunciation_confidence():
    quality = build_assessment_quality(
        {"provider": "ensemble", "provider_hypotheses": [{}, {}], "ensemble_agreement": .94},
        [{"id": "w1", "timing_valid": True}, {"id": "w2", "timing_valid": True}],
        [], _criteria(),
    )
    assert quality["scope"] == "language_criteria_only"
    assert quality["pronunciation_audio_grounded"] is False
    assert quality["coverage_score_is_probability"] is False
    assert any("pronunciation" in reason for reason in quality["blockers_vi"])


def test_quality_drops_when_providers_disagree_and_many_words_are_uncertain():
    words = [{"id": f"w{i}", "timing_valid": True} for i in range(10)]
    uncertain = [{"word_id": f"w{i}"} for i in range(4)]
    quality = build_assessment_quality(
        {"provider": "ensemble", "provider_hypotheses": [{}, {}], "ensemble_agreement": .5},
        words, uncertain, _criteria(6.0),
    )
    assert quality["level"] == "low"
    assert quality["uncertain_word_ratio"] == .4
    assert len(quality["blockers_vi"]) >= 2
