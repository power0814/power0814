"""ffmpeg로 읽고, wave로 쓰고, 간단한 신호 측정을 한다."""

from __future__ import annotations

import json
import subprocess
import wave
from math import gcd
from pathlib import Path

import numpy as np

AUDIO_EXTS = {
    ".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".webm",
    ".mp4", ".mkv", ".mov", ".ts", ".flv",
}


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def load(path: Path, sr: int, channels: int = 1, start: float | None = None,
         duration: float | None = None) -> np.ndarray:
    """(channels, samples) float32. start/duration은 초 단위로 잘라 읽는다."""
    cmd = ["ffmpeg", "-nostdin", "-v", "error"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    if duration:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-i", str(path), "-vn", "-f", "f32le", "-ac", str(channels), "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).T.copy()


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x
    from scipy.signal import resample_poly

    g = gcd(sr_in, sr_out)
    return resample_poly(x, sr_out // g, sr_in // g, axis=-1).astype(np.float32)


def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    """모노 float32 → 16비트 PCM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1.0, 1.0) * 32767).astype("<i2")
    tmp = path.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    tmp.replace(path)


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, path
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    return x, sr


def db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-10)))


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if x.size else 0.0


def measure(voice: np.ndarray, bgm: np.ndarray | None) -> dict:
    """구간 하나의 품질 지표.

    - rms_db, peak_db: 목소리 크기
    - clip: |x| ≥ 0.99인 샘플 비율 (원본이 찢어졌는지)
    - bgm_db: 분리된 배경음 RMS − 목소리 RMS. 클수록 배경음이 목소리에 가깝게 컸다는 뜻이고,
      그만큼 분리 잔여물이 남았을 가능성이 높다.
    """
    v = rms(voice)
    m = {
        "rms_db": round(db(v), 2),
        "peak_db": round(db(float(np.max(np.abs(voice))) if voice.size else 0.0), 2),
        "clip": round(float(np.mean(np.abs(voice) >= 0.99)) if voice.size else 0.0, 5),
    }
    m["bgm_db"] = round(db(rms(bgm)) - db(v), 2) if bgm is not None else -100.0
    return m


def normalize_loudness(x: np.ndarray, target_db: float = -20.0, peak_db: float = -1.0) -> np.ndarray:
    """RMS를 target_db로 맞추되 피크가 peak_db를 넘지 않게 한다."""
    r = rms(x)
    if r <= 0:
        return x
    gain = 10 ** (target_db / 20) / r
    peak = float(np.max(np.abs(x))) * gain
    limit = 10 ** (peak_db / 20)
    if peak > limit:
        gain *= limit / peak
    return (x * gain).astype(np.float32)
