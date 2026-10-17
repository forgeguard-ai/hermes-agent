"""Fork-owned tests: TTS chunking modes (``tools/tts_chunking_modes.py``).

``tts.streaming.chunking`` picks how streamed speech is cut: ``punctuation``
(default), ``paragraphs`` or ``none`` (Open WebUI ``audio.tts.split_on``
parity). The mode is applied to upstream's ``SentenceChunker`` through its
``boundary`` attribute; these cases pin the cutting behavior and the config
resolution.
"""

import re

import pytest

import tools.tts_chunking_modes as modes
import tools.tts_streaming as ts


class TestSentenceChunkerModes:
    def test_paragraphs_mode_cuts_on_every_line_break_run(self):
        c = modes.chunker_for_mode("paragraphs")
        got = c.feed(
            "line one is long enough\nline two is long enough\n\nline three is long enough\n"
        )
        assert got == [
            "line one is long enough\n",
            "line two is long enough\n\n",
            "line three is long enough\n",
        ]
        assert c.flush() == []

    def test_paragraphs_mode_merges_short_lines_forward(self):
        c = modes.apply_chunking_mode(ts.SentenceChunker(min_len=20), "paragraphs")
        got = c.feed("Ha!\nokay the second line is long enough\n")
        assert got == ["Ha!\nokay the second line is long enough\n"]

    def test_none_mode_buffers_everything_until_flush(self):
        c = modes.chunker_for_mode("none")
        assert c.feed("First sentence here. ") == []
        assert c.feed("Second one!\nAnd a third?") == []
        assert c.flush() == ["First sentence here. Second one!\nAnd a third?"]
        assert c.flush() == []

    def test_think_blocks_stripped_in_paragraphs_and_none_modes(self):
        for mode in ("paragraphs", "none"):
            c = modes.chunker_for_mode(mode)
            assert c.feed("<think>secret plan") == []
            got = c.feed(" more secret</think>spoken text that is long enough\n")
            if mode == "paragraphs":
                assert got == ["spoken text that is long enough\n"]
            else:
                assert got == []
                assert c.flush() == ["spoken text that is long enough"]

    def test_punctuation_mode_matches_the_plain_chunker(self):
        text = "First sentence is long enough. Second one is long enough too!\nTail"
        plain = ts.SentenceChunker()
        moded = modes.chunker_for_mode("punctuation")
        assert moded.feed(text) == plain.feed(text)
        assert moded.flush() == plain.flush()

    def test_mode_is_recorded_on_the_chunker(self):
        for mode in ("punctuation", "paragraphs", "none"):
            assert modes.chunker_for_mode(mode).mode == mode


class TestBoundaryForMode:
    def test_punctuation_uses_the_chunker_default(self):
        assert modes.boundary_for_mode("punctuation") is None

    def test_paragraphs_cuts_on_line_break_runs(self):
        assert modes.boundary_for_mode("paragraphs") is modes.PARAGRAPH_BOUNDARY_RE
        assert modes.PARAGRAPH_BOUNDARY_RE.pattern == r"\n+"

    def test_none_never_matches(self):
        boundary = modes.boundary_for_mode("none")
        assert boundary.search("a. b!\n\nc", 0) is None


class TestResolveChunkingMode:
    def test_absent_config_defaults_to_punctuation(self):
        assert modes.resolve_chunking_mode({}) == "punctuation"
        assert modes.resolve_chunking_mode({"streaming": {}}) == "punctuation"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("punctuation", "punctuation"),
            ("sentence", "punctuation"),
            ("paragraphs", "paragraphs"),
            ("paragraph", "paragraphs"),
            ("none", "none"),
            ("whole", "none"),
            ("off", "none"),
            ("  Paragraphs  ", "paragraphs"),
        ],
    )
    def test_aliases_normalize(self, raw, expected):
        assert modes.resolve_chunking_mode({"streaming": {"chunking": raw}}) == expected

    def test_garbage_falls_back_to_punctuation(self):
        assert modes.resolve_chunking_mode({"streaming": {"chunking": "sometimes"}}) == "punctuation"

    def test_non_dict_streaming_section_is_tolerated(self):
        assert modes.resolve_chunking_mode({"streaming": "paragraphs"}) == "punctuation"
        assert modes.resolve_chunking_mode({"streaming": None}) == "punctuation"


class TestChunkerForConfig:
    def test_builds_a_sentence_chunker_in_the_configured_mode(self):
        c = modes.chunker_for_config({"streaming": {"chunking": "paragraphs"}})
        assert isinstance(c, ts.SentenceChunker)
        assert c.mode == "paragraphs"
        assert c.feed("a line that is long enough\nrest") == ["a line that is long enough\n"]

    def test_default_config_is_punctuation(self):
        c = modes.chunker_for_config({})
        assert c.mode == "punctuation"
        assert c.boundary is None

    def test_prefers_an_upstream_from_config_constructor(self, monkeypatch):
        seen = {}

        def from_config(cfg):
            seen["cfg"] = cfg
            return ts.SentenceChunker(min_len=5)

        monkeypatch.setattr(ts.SentenceChunker, "from_config", from_config, raising=False)
        cfg = {"streaming": {"chunking": "none"}}
        c = modes.chunker_for_config(cfg)
        assert seen["cfg"] is cfg
        assert c.min_len == 5
        assert c.mode == "none"


def test_feed_hook_reads_the_boundary_attribute():
    """The one fork line inside ``SentenceChunker.feed``: a per-instance
    ``boundary`` replaces the sentence regex; absent or ``None`` keeps it."""
    c = ts.SentenceChunker(min_len=1)
    c.boundary = re.compile(r";")
    assert c.feed("a; b. c;") == ["a;", " b. c;"]
