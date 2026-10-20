"""Context suggestions preserve what was heard and never become scored errors."""
import json
from unittest.mock import patch

import pytest

from app.core.config import Settings, settings
from app.modules.speaking.assessment import transcript_review as review


def words(text):
    return [{'id': f'w{i+1}', 'word': token, 'text': token, 'start': i, 'end': i + .8}
            for i, token in enumerate(text.split())]


def test_context_proposal_preserves_original_and_requires_confirmation(monkeypatch):
    monkeypatch.setattr(settings, 'llm_provider', 'gemini')
    tokens = words('I am still in Ghana')
    response = {'suggestions': [{
        'quote': 'Ghana', 'word_ids': ['w5'], 'replacement': 'Đà Nẵng',
        'reason_vi': 'Tên địa danh bạn cung cấp; cần nghe lại để phân biệt.',
        'kind': 'proper_name', 'source': 'provided_term',
    }]}
    with patch.object(review, 'provider_complete', return_value=json.dumps(response)):
        result = review.review_transcript('Where do you live?', tokens, [], ['Đà Nẵng'], [])
    assert tokens[-1]['word'] == 'Ghana'
    assert result['suggestions'][0]['replacement'] == 'Đà Nẵng'
    assert result['suggestions'][0]['status'] == 'pending'


def test_unknown_place_cannot_be_replaced_from_context_alone(monkeypatch):
    monkeypatch.setattr(settings, 'llm_provider', 'gemini')
    response = {'suggestions': [{
        'quote': 'Ghana', 'word_ids': ['w1'], 'replacement': 'Đà Nẵng',
        'reason_vi': 'Đoán theo quốc tịch.', 'kind': 'proper_name', 'source': 'context_only',
    }]}
    with patch.object(review, 'provider_complete', return_value=json.dumps(response)):
        result = review.review_transcript('Where?', words('Ghana'), [], [], [])
    assert result['status'] == 'unavailable'
    assert result['suggestions'] == []


def test_proposal_cannot_fabricate_or_reorder_source_words(monkeypatch):
    monkeypatch.setattr(settings, 'llm_provider', 'gemini')
    response = {'suggestions': [{
        'quote': 'I Ghana', 'word_ids': ['w1', 'w3'], 'replacement': 'I study',
        'reason_vi': 'Không hợp lệ.', 'kind': 'possible_mishearing', 'source': 'context_only',
    }]}
    with patch.object(review, 'provider_complete', return_value=json.dumps(response)):
        assert review.review_transcript('Q', words('I love Ghana'), [], [], [])['status'] == 'unavailable'


def test_configuration_uses_one_root_env_from_any_working_directory(tmp_path, monkeypatch):
    from app.core.config import ROOT_ENV_FILE

    (tmp_path / '.env').write_text('GEMINI_MODEL=wrong-local-model\n')
    monkeypatch.chdir(tmp_path)
    configured = Settings()
    root_configured = Settings(_env_file=ROOT_ENV_FILE)
    assert configured.gemini_model == root_configured.gemini_model
    assert configured.gemini_model != 'wrong-local-model'


def test_rejected_context_review_never_discards_the_rest_of_the_assessment(monkeypatch):
    from app.modules.speaking.assessment import engine

    monkeypatch.setattr(settings, 'stt_provider', 'mock')
    monkeypatch.setattr(settings, 'llm_provider', 'mock')
    with patch.object(engine, 'review_transcript', return_value={
        'status': 'unavailable', 'suggestions': [], 'keyterms': [],
    }), patch.object(engine.budget, 'record'):
        result = engine.grade_speaking('dummy.webm', 'Q', 'PART 1')
    assert result['transcript_review']['status'] == 'unavailable'
    assert result['grammar']['band'] is not None


def test_context_proposals_are_excluded_from_scored_error_evidence(monkeypatch):
    from app.modules.speaking.assessment import engine

    monkeypatch.setattr(settings, 'stt_provider', 'mock')
    monkeypatch.setattr(settings, 'llm_provider', 'mock')
    proposal = {
        'quote': 'This', 'word_ids': ['w1'], 'replacement': 'It',
        'reason_vi': 'Cần nghe lại.', 'kind': 'possible_mishearing',
        'source': 'context_only', 'status': 'pending', 'confirmed_text': None,
    }
    original = engine.raters.assess_speaking
    captured = []

    def assess(*args, **kwargs):
        captured.extend(kwargs['uncertain_spans'])
        return original(*args, **kwargs)

    with patch.object(engine, 'review_transcript', return_value={
        'status': 'ready', 'suggestions': [proposal], 'keyterms': [],
    }), patch.object(engine.raters, 'assess_speaking', side_effect=assess), patch.object(engine.budget, 'record'):
        result = engine.grade_speaking('dummy.webm', 'Q', 'PART 1')
    assert any(s['word_id'] == 'w1' and s['reason'] == 'contextual_asr_review' for s in captured)
    assert result['transcript'].startswith('This ')
    assert result['color_coded_transcript'][0]['uncertain'] is True
    assert all('w1' not in e['word_ids'] for e in result['grammar']['evidence'])


@pytest.fixture
def saved_session():
    import uuid
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    from app.modules.speaking.models import PracticeSession

    Base.metadata.create_all(bind=engine)
    result = {
        'schema_version': 'speaking-v3', 'status': 'partial', 'overall': None,
        'transcript': 'I am still in Ghana', 'color_coded_transcript': words('I am still in Ghana'),
        'grammar': {'band': 6.0, 'errors': []},
        'transcript_review': {'status': 'ready', 'keyterms': ['Đà Nẵng'], 'suggestions': [{
            'quote': 'Ghana', 'word_ids': ['w5'], 'replacement': 'Đà Nẵng',
            'reason_vi': 'Tên bạn cung cấp; cần nghe lại.', 'kind': 'proper_name',
            'source': 'provided_term', 'status': 'pending', 'confirmed_text': None,
        }]},
    }
    with SessionLocal() as db:
        session = PracticeSession(id=str(uuid.uuid4()), student_name='Review Student', result=result,
                                  transcript=result['transcript'])
        db.add(session)
        db.commit()
        return session.id, result


def test_review_accept_and_dismiss_persist_without_rewriting_or_rescoring(saved_session):
    from fastapi.testclient import TestClient
    from app.main import app

    session_id, original = saved_session
    path = f'/api/v1/speaking/practice/{session_id}'
    with TestClient(app) as client:
        accepted = client.patch(path + '/transcript-review', json={
            'student_name': 'Review Student', 'word_ids': ['w5'], 'action': 'accepted',
            'replacement': 'Da Nang',
        })
        assert accepted.status_code == 200
        result = client.get(path).json()['result']
        assert result['transcript'] == original['transcript']
        assert result['grammar'] == original['grammar']
        assert result['overall'] is None
        assert result['transcript_review']['suggestions'][0]['confirmed_text'] == 'Da Nang'
        assert result['transcript_review']['suggestions'][0]['status'] == 'accepted'
        rejected = client.patch(path + '/transcript-review', json={
            'student_name': 'Review Student', 'word_ids': ['w5'], 'action': 'dismissed',
        })
        assert rejected.status_code == 200
        assert rejected.json()['result']['transcript_review']['suggestions'][0]['confirmed_text'] is None


@pytest.mark.parametrize('decision,status', [
    ({'student_name': 'Someone else', 'word_ids': ['w5'], 'replacement': 'Da Nang'}, 404),
    ({'word_ids': ['missing'], 'replacement': 'Da Nang'}, 422),
    ({'word_ids': ['w3', 'w5'], 'replacement': 'studying in Da Nang'}, 422),
    ({'word_ids': ['w5'], 'replacement': '   '}, 422),
    ({'word_ids': ['w4', 'w5'], 'replacement': 'in Da Nang'}, 409),
])
def test_review_rejects_invalid_or_overlapping_edits(saved_session, decision, status):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.patch(f'/api/v1/speaking/practice/{saved_session[0]}/transcript-review', json={
            'student_name': 'Review Student', 'action': 'accepted', **decision,
        })
        assert response.status_code == status
