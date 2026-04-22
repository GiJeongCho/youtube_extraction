#!/usr/bin/env python3
"""YouTube 다운로더 웹 서버 — FastAPI + SSE 진행률"""

import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="YouTube Downloader")

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

AUDIO_FORMATS: set[str] = {"mp3", "wav", "flac", "aac", "m4a", "opus", "vorbis"}
VIDEO_FORMATS: set[str] = {"mp4", "mkv", "webm", "avi"}
ALL_FORMATS: set[str] = AUDIO_FORMATS | VIDEO_FORMATS

SUPPORTED_FORMATS: dict[str, dict] = {
    "mp3": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]},
    "wav": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}]},
    "flac": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "flac"}]},
    "aac": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "aac", "preferredquality": "192"}]},
    "m4a": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]},
    "opus": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "opus"}]},
    "vorbis": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "vorbis"}]},
    "mp4": {"merge_output_format": "mp4"},
    "mkv": {"merge_output_format": "mkv"},
    "webm": {"merge_output_format": "webm"},
    "avi": {"merge_output_format": "avi"},
}

tasks: dict[str, dict] = {}


class DownloadRequest(BaseModel):
    url: str
    format: str = "mp4"
    quality: str = "best"

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        v = v.lower()
        if v not in ALL_FORMATS:
            raise ValueError(f"지원하지 않는 형식: {v}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL이 비어있습니다")
        return v


def _build_opts(fmt: str, output_dir: str, quality: str, progress_hook: Optional[callable] = None) -> dict:
    opts: dict = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    if fmt in AUDIO_FORMATS:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = SUPPORTED_FORMATS[fmt]["postprocessors"]
    else:
        if quality == "best":
            opts["format"] = "bestvideo+bestaudio/best"
        elif quality == "worst":
            opts["format"] = "worstvideo+worstaudio/worst"
        else:
            opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        opts["merge_output_format"] = SUPPORTED_FORMATS[fmt]["merge_output_format"]

    return opts


def _extract_info(url: str) -> dict:
    """영상 메타데이터만 추출 (다운로드 없이)"""
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "Unknown"),
        }


def _do_download(task_id: str, url: str, fmt: str, quality: str) -> None:
    task = tasks[task_id]
    task_dir = str(DOWNLOAD_DIR / task_id)
    os.makedirs(task_dir, exist_ok=True)

    def progress_hook(d: dict) -> None:
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total > 0 else 0
            speed = d.get("speed", 0) or 0
            eta = d.get("eta", 0) or 0
            task.update({
                "progress": round(pct, 1),
                "speed": speed,
                "eta": eta,
                "status": "downloading",
            })
        elif d["status"] == "finished":
            task["status"] = "processing"
            task["progress"] = 100
            task["filename"] = d.get("filename", "")

    try:
        info = _extract_info(url)
        task["title"] = info["title"]
        task["thumbnail"] = info["thumbnail"]
        task["uploader"] = info["uploader"]
        task["duration"] = info["duration"]

        opts = _build_opts(fmt, task_dir, quality, progress_hook)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        downloaded_files = list(Path(task_dir).iterdir())
        if downloaded_files:
            final_file = downloaded_files[0]
            task["filename"] = final_file.name
            task["filepath"] = str(final_file)
            task["status"] = "done"
        else:
            task["status"] = "error"
            task["error"] = "파일을 찾을 수 없습니다"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/download")
async def start_download(req: DownloadRequest) -> dict:
    task_id = uuid.uuid4().hex[:12]
    tasks[task_id] = {
        "status": "starting",
        "progress": 0,
        "title": "",
        "filename": "",
        "filepath": "",
        "error": "",
        "format": req.format,
        "speed": 0,
        "eta": 0,
    }
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _do_download, task_id, req.url, req.format, req.quality)
    return {"task_id": task_id}


@app.get("/api/progress/{task_id}")
async def progress_stream(task_id: str) -> StreamingResponse:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    async def event_generator():
        while True:
            task = tasks.get(task_id)
            if not task:
                break
            data = json.dumps(task, ensure_ascii=False)
            yield f"data: {data}\n\n"
            if task["status"] in ("done", "error"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/file/{task_id}")
async def download_file(task_id: str) -> FileResponse:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    if task["status"] != "done":
        raise HTTPException(status_code=400, detail="아직 다운로드가 완료되지 않았습니다")

    filepath = task["filepath"]
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    return FileResponse(
        path=filepath,
        filename=task["filename"],
        media_type="application/octet-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=4995, reload=True)
