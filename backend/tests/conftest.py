import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="lexilearn-test-")
os.environ["TEACHER_ACCESS_CODE"] = "test-code"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = _tmp
os.environ["STT_PROVIDER"] = "groq"
os.environ["GROQ_API_KEY"] = ""
os.environ["WHISPER_PRELOAD"] = "false"
os.environ["SPEAKING_ASYNC_DEFAULT"] = "false"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["GOOGLE_API_KEY"] = ""
