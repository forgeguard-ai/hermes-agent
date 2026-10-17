"""Fork-owned tests: OpenAI streaming-TTS request shaping
(``tools/tts_openai_stream_request.py``).

End-to-end coverage through ``OpenAIStreamer.stream`` stays in
``tests/tools/test_tts_streaming.py`` (``test_openai_streamer_*``); these
cases pin the helper itself.
"""

from tools.tts_openai_stream_request import openai_stream_request
from tools.tts_tool import DEFAULT_OPENAI_BASE_URL


def test_defaults_target_the_public_api_never_the_llm_override(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://llm.example/v1")
    base_url, kwargs = openai_stream_request({}, {}, "hello")
    assert base_url == DEFAULT_OPENAI_BASE_URL
    assert kwargs == {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "input": "hello",
        "response_format": "pcm",
    }


def test_configured_endpoint_model_and_voice():
    section = {"base_url": "http://127.0.0.1:8880/v1", "model": "kokoro", "voice": "af_bella"}
    base_url, kwargs = openai_stream_request(section, {}, "hi")
    assert base_url == "http://127.0.0.1:8880/v1"
    assert kwargs["model"] == "kokoro"
    assert kwargs["voice"] == "af_bella"


def test_speed_precedence_and_clamp():
    assert "speed" not in openai_stream_request({}, {"speed": 1.0}, "x")[1]
    assert openai_stream_request({}, {"speed": 2.0}, "x")[1]["speed"] == 2.0
    assert openai_stream_request({"speed": 10}, {"speed": 2.0}, "x")[1]["speed"] == 4.0
    assert openai_stream_request({"speed": 0.1}, {}, "x")[1]["speed"] == 0.25


def test_bad_speed_falls_back_to_default():
    assert "speed" not in openai_stream_request({"speed": "fast"}, {}, "x")[1]


def test_language_rides_as_lang_code():
    _, kwargs = openai_stream_request({"language": "es"}, {}, "hola")
    assert kwargs["extra_body"] == {"lang_code": "es"}
    _, kwargs = openai_stream_request({"language": ""}, {}, "hola")
    assert "extra_body" not in kwargs
