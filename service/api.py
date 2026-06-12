"""TeachingMonster API server.

Provides FastAPI endpoints for video generation and retrieval.
Supports DEV (Ollama-hosted models) and PROD (OpenAI models) environments,
as well as a dry-run connection test via the X-Dry-Run header.
"""

import os
from pydantic import BaseModel
from typing import Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from service.storage import CloudStorage

from src.io.path_definition import get_project_dir
from service.worker import VideoWorker


app = FastAPI(title="TeachingMonster API")

class VideoGenerateRequest(BaseModel):
    """Request payload for video generation.

    Attributes:
        request_id: Unique identifier for the generation request.
        course_requirement: Description of the course topic and learning goals.
        student_persona: Description of the target student's grade level and background.
    """
    request_id: str
    course_requirement: str
    student_persona: str


class VideoGenerateResponse(BaseModel):
    """Response returned after video generation.

    Attributes:
        video_url: Presigned S3 URL for downloading the generated video.
        subtitle_url: URL for subtitles file, if available.
        supplementary_url: URL for supplementary materials, if available.
    """
    video_url: str
    subtitle_url: Optional[str] = None
    supplementary_url: Optional[str] = None


@app.post("/v1/dev/video/generate", response_model=VideoGenerateResponse)
async def start_generation(request: VideoGenerateRequest, ori_req: Request):
    """Start video generation in DEV mode (Ollama-hosted models).

    Runs the full pipeline synchronously and returns the S3 video URL.

    Args:
        request: VideoGenerateRequest with course_requirement and student_persona.
        ori_req: Raw FastAPI Request for header inspection (X-Dry-Run).

    Returns:
        VideoGenerateResponse with the presigned S3 video URL.
    """
    if ori_req.headers.get("X-Dry-Run") == "true":
        print("[Log] Dry Run / Connection Test received; start_generation")
        return {
            "video_url": "https://example.com/test.mp4",
            "subtitle_url": "https://example.com/test.srt",
            "supplementary_url": None
        }

    env = "DEV"

    worker = VideoWorker(env=env)

    _ = await worker.process_request(request)

    url = worker.jobs[request.request_id]['url']

    return VideoGenerateResponse(
            video_url=url,
            subtitle_url=None,
            supplementary_url=None,
        )


@app.post("/v1/prod/video/generate", response_model=VideoGenerateResponse)
async def start_generation(request: VideoGenerateRequest, ori_req: Request):
    """Start video generation in PROD mode (OpenAI models).

    Runs the full pipeline synchronously and returns the S3 video URL.

    Args:
        request: VideoGenerateRequest with course_requirement and student_persona.
        ori_req: Raw FastAPI Request for header inspection (X-Dry-Run).

    Returns:
        VideoGenerateResponse with the presigned S3 video URL.
    """
    if ori_req.headers.get("X-Dry-Run") == "true":
        print("[Log] Dry Run / Connection Test received; start_generation")
        return {
            "video_url": "https://example.com/test.mp4",
            "subtitle_url": "https://example.com/test.srt",
            "supplementary_url": None
        }

    env = "PROD"

    worker = VideoWorker(env=env)

    _ = await worker.process_request(request)

    url = worker.jobs[request.request_id]['url']

    return VideoGenerateResponse(
        video_url=url,
        subtitle_url=None,
        supplementary_url=None,
    )


@app.post("/v1/files/{request_id}/video", response_model=VideoGenerateResponse)
async def get_video(request_id: str, ori_req: Request):
    """Retrieve the S3 URL for a previously generated video.

    Does not re-run the pipeline. Uploads the existing local file
    to S3 and returns a fresh presigned URL.

    Args:
        request_id: The unique request identifier from the original generation.
        ori_req: Raw FastAPI Request for header inspection (X-Dry-Run).

    Returns:
        VideoGenerateResponse with the presigned S3 video URL.
    """

    cloud_storage = CloudStorage()

    local_path = os.path.join(get_project_dir(), "data", request_id, "video", f"final_presentation_{request_id}.mp4")

    url = cloud_storage.upload_file(local_path=local_path)

    return VideoGenerateResponse(
            video_url=url,
            subtitle_url=None,
            supplementary_url=None,
        )


@app.post("/test", response_model=VideoGenerateResponse)
async def test_api_connection(request_id: str, ori_req: Request):
    """Retrieve the S3 URL for a previously generated video.

    Does not re-run the pipeline. Uploads the existing local file
    to S3 and returns a fresh presigned URL.

    Args:
        request_id: The unique request identifier from the original generation.
        ori_req: Raw FastAPI Request for header inspection (X-Dry-Run).

    Returns:
        VideoGenerateResponse with the presigned S3 video URL.

    Teaching Monster 測試:
    https://coexist-secluding-swell.ngrok-free.dev/test?request_id=test
    """
    from time import sleep

    sleep(300)

    print(f"[Log] Dry Run / Connection Test received; request_id: TEST")
    return {
        "video_url": "https://example.com/test.mp4",
        "subtitle_url": "https://example.com/test.srt",
        "supplementary_url": None
    }


if __name__ == "__main__":

    # 本地連線測試
    # curl.exe -X POST "http://127.0.0.1:8000/test?request_id=test"

    """
    New-NetFirewallRule `
    >>   -DisplayName "FastAPI 8000" `
    >>   -Direction Inbound `
    >>   -Protocol TCP `
    >>   -LocalPort 8000 `
    >>   -Action Allow
    """

    # uvicorn service.api:app --host 0.0.0.0 --port 8000
    # ngrok http 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
