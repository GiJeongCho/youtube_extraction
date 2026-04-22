#!/usr/bin/env python3
"""YouTube 동영상/오디오 다운로더 — yt-dlp 기반"""

import argparse
import sys
import os
from pathlib import Path

import yt_dlp

SUPPORTED_FORMATS = {
    # 오디오
    "mp3": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]},
    "wav": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}]},
    "flac": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "flac"}]},
    "aac": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "aac", "preferredquality": "192"}]},
    "m4a": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]},
    "opus": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "opus"}]},
    "vorbis": {"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "vorbis"}]},
    # 비디오
    "mp4": {"merge_output_format": "mp4"},
    "mkv": {"merge_output_format": "mkv"},
    "webm": {"merge_output_format": "webm"},
    "avi": {"merge_output_format": "avi"},
}

AUDIO_FORMATS = {"mp3", "wav", "flac", "aac", "m4a", "opus", "vorbis"}
VIDEO_FORMATS = {"mp4", "mkv", "webm", "avi"}


def build_opts(fmt: str, output_dir: str, quality: str) -> dict:
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    opts: dict = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }

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


def download(url: str, fmt: str, output_dir: str, quality: str) -> None:
    opts = build_opts(fmt, output_dir, quality)
    with yt_dlp.YoutubeDL(opts) as ydl:
        print(f"\n{'='*60}")
        print(f"  URL      : {url}")
        print(f"  형식     : {fmt}")
        print(f"  저장 경로: {os.path.abspath(output_dir)}")
        if fmt in VIDEO_FORMATS:
            print(f"  화질     : {quality}")
        print(f"{'='*60}\n")
        ydl.download([url])
    print("\n✅ 다운로드 완료!\n")


def interactive_mode() -> None:
    """대화형 모드: 터미널에서 직접 입력받아 다운로드"""
    print("=" * 60)
    print("  YouTube 다운로더 (대화형 모드)")
    print("=" * 60)

    url = input("\n유튜브 링크를 입력하세요: ").strip()
    if not url:
        print("❌ URL이 비어있습니다.")
        sys.exit(1)

    print("\n지원 형식:")
    print(f"  오디오: {', '.join(sorted(AUDIO_FORMATS))}")
    print(f"  비디오: {', '.join(sorted(VIDEO_FORMATS))}")
    fmt = input("\n원하는 형식을 입력하세요 (기본: mp4): ").strip().lower() or "mp4"

    if fmt not in SUPPORTED_FORMATS:
        print(f"❌ 지원하지 않는 형식입니다: {fmt}")
        print(f"   지원 형식: {', '.join(sorted(SUPPORTED_FORMATS.keys()))}")
        sys.exit(1)

    output_dir = input("저장 경로를 입력하세요 (기본: ./downloads): ").strip() or "./downloads"

    quality = "best"
    if fmt in VIDEO_FORMATS:
        quality = input("화질을 선택하세요 (best/worst/720/1080 등, 기본: best): ").strip() or "best"

    download(url, fmt, output_dir, quality)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube 동영상/오디오 다운로더",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
지원 형식:
  오디오: {', '.join(sorted(AUDIO_FORMATS))}
  비디오: {', '.join(sorted(VIDEO_FORMATS))}

사용 예시:
  %(prog)s https://youtu.be/xxx                    # mp4로 다운로드
  %(prog)s https://youtu.be/xxx -f mp3              # mp3로 다운로드
  %(prog)s https://youtu.be/xxx -f wav -o ./music   # wav로 ./music 에 저장
  %(prog)s https://youtu.be/xxx -f mp4 -q 720       # 720p mp4로 다운로드
  %(prog)s -i                                       # 대화형 모드
""",
    )
    parser.add_argument("url", nargs="?", help="유튜브 링크")
    parser.add_argument("-f", "--format", default="mp4", choices=sorted(SUPPORTED_FORMATS.keys()), help="출력 형식 (기본: mp4)")
    parser.add_argument("-o", "--output", default="./downloads", help="저장 경로 (기본: ./downloads)")
    parser.add_argument("-q", "--quality", default="best", help="비디오 화질 (best/worst/720/1080 등, 기본: best)")
    parser.add_argument("-i", "--interactive", action="store_true", help="대화형 모드로 실행")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    if not args.url:
        parser.print_help()
        sys.exit(1)

    download(args.url, args.format, args.output, args.quality)


if __name__ == "__main__":
    main()
