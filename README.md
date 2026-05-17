# YouTube 다운로더

유튜브 링크를 입력하면 원하는 형식으로 동영상 또는 오디오를 다운로드합니다.

## 지원 형식

| 종류 | 형식 |
|------|------|
| 오디오 | mp3, wav, flac, aac, m4a, opus, vorbis |
| 비디오 | mp4, mkv, webm, avi |

## 설치

[uv](https://docs.astral.sh/uv/)를 사용하여 가상환경을 생성하고 의존성을 설치합니다.

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성 + 의존성 설치
uv sync
```

> **참고:** 오디오 변환(mp3, wav 등)이나 비디오 포맷 병합에는 [FFmpeg](https://ffmpeg.org/)가 필요합니다.
>
> ```bash
> # Ubuntu/Debian
> sudo apt install ffmpeg
>
> # macOS (Homebrew)
> brew install ffmpeg
> ```

## 사용법

### 명령줄 모드

```bash
# 기본 (mp4)
uv run python downloader.py https://youtu.be/xxx

# mp3로 다운로드
uv run python downloader.py https://youtu.be/xxx -f mp3

# wav로 특정 경로에 저장
uv run python downloader.py https://youtu.be/xxx -f wav -o ./music

# 720p mp4로 다운로드
uv run python downloader.py https://youtu.be/xxx -f mp4 -q 720
```

### 대화형 모드

```bash
uv run python downloader.py -i
```

터미널에서 URL, 형식, 저장 경로 등을 차례로 입력할 수 있습니다.

### 웹 UI 모드 (포트 4995)

```bash
uv run python server.py
```

브라우저에서 `http://localhost:4995` 접속 후:

1. 유튜브 링크 붙여넣기
2. 형식(mp4, mp3, wav 등) · 화질 선택
3. "다운로드 시작" 클릭 → 실시간 진행률 확인
4. 완료 후 "파일 다운로드" 클릭 → 브라우저 다운로드 목록에 저장

### 전체 옵션 (CLI)

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `url` | 유튜브 링크 | — |
| `-f`, `--format` | 출력 형식 | mp4 |
| `-o`, `--output` | 저장 경로 | ./downloads |
| `-q`, `--quality` | 비디오 화질 (best/worst/720/1080 등) | best |
| `-i`, `--interactive` | 대화형 모드 | — |


## 파이프라인
```
cd /d d:\D_project\project\yd_extraction
uv sync
uv run python server.py

http://localhost:4996