"""Register every ORM model against the single application Base."""

from app.modules.assignments.models import Assignment  # noqa: F401
from app.modules.classes.models import Class  # noqa: F401
from app.modules.speaking.legacy_models import ExamSet, Question, Topic  # noqa: F401
from app.modules.speaking.models import (  # noqa: F401
    PracticeSession,
    SpeakingAssessmentJob,
    SpeakingMockSession,
    SpeakingQuestion,
    SpeakingTopic,
    SpeakingTurn,
)
from app.modules.submissions.models import Submission  # noqa: F401
