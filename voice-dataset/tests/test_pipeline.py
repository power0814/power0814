import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import synth  # noqa: E402

from vds import audio  # noqa: E402
from vds.export import Rules, export, judge  # noqa: E402
from vds.process import Params, find_sources, process_source  # noqa: E402
from vds.separate import Passthrough  # noqa: E402
from vds.transcribe import transcribe_all  # noqa: E402
from vds.vad import merge_segments  # noqa: E402

DIM = 192
REF = np.eye(DIM, dtype=np.float32)[0]


def f0(x, sr=16000):
    x = x - x.mean()
    ac = np.correlate(x[: sr], x[: sr], "full")[len(x[: sr]) - 1:]
    lo, hi = sr // 400, sr // 80
    return sr / (lo + np.argmax(ac[lo:hi]))


def fake_embed(wavs):
    """낮은 목소리(A)는 기준 방향, 높은 목소리(B)는 직교 방향."""
    out = np.zeros((len(wavs), DIM), np.float32)
    for i, w in enumerate(wavs):
        out[i, 0 if f0(w) < 180 else 1] = 1
    return out


class FakeWhisper:
    def transcribe(self, path, **kw):
        seg = SimpleNamespace(text=" 안녕하세요 오늘도 방송 시작", avg_logprob=-0.2,
                              no_speech_prob=0.01, compression_ratio=1.1)
        return iter([seg]), None


def test_merge_segments():
    spans = [(0.0, 1.0), (1.2, 2.0), (2.1, 3.0), (5.0, 5.5), (6.0, 20.0)]
    assert merge_segments(spans, 0.4, 1.5, 12.0) == [(0.0, 3.0)]
    # max_dur을 넘기게 되면 붙이지 않는다
    assert merge_segments([(0, 5), (5.1, 9)], 0.4, 1.0, 8.0) == [(0, 5), (5.1, 9)]


def test_measure_and_normalize():
    x = 0.1 * np.ones(1000, np.float32)
    m = audio.measure(x, 0.01 * np.ones(1000, np.float32))
    assert abs(m["rms_db"] + 20) < 0.01 and abs(m["bgm_db"] + 20) < 0.01 and m["clip"] == 0
    y = audio.normalize_loudness(np.r_[np.full(10, 0.9), np.full(990, 0.01)].astype(np.float32), -20)
    assert np.abs(y).max() <= 10 ** (-1 / 20) + 1e-6


@pytest.mark.parametrize("text,why", [
    ("ㅋㅋㅋㅋ", "laugh_only"),
    ("하하하하", "laugh_only"),
    ("시청해 주셔서 감사합니다.", "hallucination"),
    ("아 진짜 이거 왜 이래", None),
])
def test_judge_text(text, why):
    seg = {"dur": 3.0, "bgm_db": -30, "rms_db": -20}
    tr = {"text": text, "logprob": -0.2, "no_speech": 0.0, "compression": 1.0}
    assert judge(seg, tr, 0.9, Rules()) == why


def test_judge_signal():
    seg = {"dur": 3.0, "bgm_db": -30, "rms_db": -20}
    tr = {"text": "아 진짜 이거 왜 이래", "logprob": -0.2, "no_speech": 0.0, "compression": 1.0}
    assert judge(seg, tr, 0.3, Rules()) == "speaker"
    assert judge({**seg, "bgm_db": -5}, tr, 0.9, Rules()) == "bgm"
    assert judge({**seg, "dur": 12.0}, {**tr, "text": "네"}, 0.9, Rules()) == "too_short_text"
    assert judge(seg, None, 0.9, Rules()) == "not_transcribed"


def test_demucs_wrapper_shapes():
    """가중치 없이 무작위 HTDemucs로 래퍼의 입출력 모양만 확인한다."""
    from demucs.htdemucs import HTDemucs

    from vds.separate import Demucs

    model = HTDemucs(sources=["drums", "bass", "other", "vocals"], channels=8,
                     t_layers=1, segment=4)
    sep = Demucs(model=model)
    mix = (0.1 * np.random.default_rng(0).standard_normal((2, 44100 * 3))).astype(np.float32)
    voice, bgm = sep(mix)
    assert voice.shape == bgm.shape == (44100 * 3,)


def test_end_to_end(tmp_path):
    work = tmp_path / "work"
    raw = work / "raw"
    raw.mkdir(parents=True)
    x = synth.program()
    audio.write_wav(raw / "vod1.wav", x, 44100)
    (raw / "vod1.info.json").write_text("{}")  # yt-dlp 부산물은 원본으로 치지 않는다

    assert list(find_sources([raw])) == ["vod1"]

    from vds.vad import SileroVAD

    # 청크를 작게 잡아 청크 경계 처리도 같이 돈다
    p = Params(chunk_sec=10.0, min_sim=0.5)
    meta = process_source("vod1", raw / "vod1.wav", work, Passthrough(), SileroVAD(), fake_embed, REF, p,
                          log=lambda *_: None)
    segs = meta["segments"]
    assert segs, meta
    assert meta["rejected"].get("speaker", 0) >= 1   # B 목소리는 버려졌다
    for s in segs:
        wav = work / "segments" / "vod1" / f"{s['name']}.wav"
        y, sr = audio.read_wav(wav)
        assert sr == 44100 and abs(len(y) / sr - s["dur"]) < 0.01
        assert f0(audio.resample(y, sr, 16000)) < 180    # 남은 건 전부 A 목소리
    assert len(np.load(work / "meta" / "vod1.npy")) == len(segs)

    # 다시 돌리면 건너뛴다
    again = process_source("vod1", raw / "vod1.wav", work, None, None, None, REF, p)
    assert again == meta

    transcribe_all(work, "", "cpu", "int8", model=FakeWhisper(), log=lambda *_: None)
    texts = json.loads((work / "meta" / "vod1.text.json").read_text())
    assert set(texts) == {s["name"] for s in segs}

    out = tmp_path / "ds"
    summary = export(work, out, "okyangi", "ko", 32000, Rules(), REF, audit=5, log=lambda *_: None)
    assert summary["kept"] == len(segs)
    lines = (out / "okyangi.list").read_text().strip().split("\n")
    assert len(lines) == len(segs)
    path, spk, lang, text = lines[0].split("|")
    assert spk == "okyangi" and lang == "ko" and text == "안녕하세요 오늘도 방송 시작"
    y, sr = audio.read_wav(Path(path))
    assert sr == 32000 and abs(audio.db(audio.rms(y)) + 20) < 1.5


def test_cli_help():
    from vds.__main__ import main

    for cmd in ["download", "reference", "process", "transcribe", "export"]:
        with pytest.raises(SystemExit) as e:
            main([cmd, "--help"])
        assert e.value.code == 0
