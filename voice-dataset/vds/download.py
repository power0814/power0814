"""yt-dlp로 오디오만 받는다. 받은 건 archive.txt에 적혀 다시 받지 않는다."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def download(work: Path, urls: list[str], batch_file: Path | None = None,
             min_duration: int = 60, max_downloads: int | None = None,
             reject_title: str | None = None, match_title: str | None = None,
             cookies_from_browser: str | None = None, cookies: Path | None = None,
             sleep: float = 1.0, extra: list[str] | None = None) -> int:
    raw = work / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestaudio/best",
        "-o", str(raw / "%(id)s.%(ext)s"),
        "--download-archive", str(work / "archive.txt"),
        "--write-info-json", "--no-overwrites", "--ignore-errors",
        "--match-filter", f"duration >=? {min_duration} & !is_live",
        "--sleep-requests", str(sleep), "--sleep-interval", str(sleep),
    ]
    if max_downloads:
        cmd += ["--max-downloads", str(max_downloads)]
    if reject_title:
        cmd += ["--reject-title", reject_title]
    if match_title:
        cmd += ["--match-title", match_title]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    if cookies:
        cmd += ["--cookies", str(cookies)]
    if batch_file:
        cmd += ["-a", str(batch_file)]
    cmd += list(extra or []) + urls
    # --max-downloads에 닿으면 101로 끝난다. 개별 영상 실패는 --ignore-errors로 넘어간다.
    return subprocess.run(cmd).returncode
