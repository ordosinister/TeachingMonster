"""Background worker that executes the video generation pipeline.

Wraps the synchronous pipeline in asyncio.to_thread() to avoid
blocking the FastAPI event loop.
"""

import os
import asyncio

from service.storage import CloudStorage
from run import main as run_pipeline

from src.io.path_definition import get_project_dir




class VideoWorker:
    """Orchestrates video generation for a single request.

    Runs the master pipeline (run.py) in a background thread and
    uploads the resulting video to S3.

    Attributes:
        jobs: Dictionary tracking job statuses by request_id.
        storage: CloudStorage instance for S3 uploads.
    """
    def __init__(self, env: str):
        self.jobs = {}
        self.storage = CloudStorage()
        os.environ["env"] = env

    async def process_request(self, request):
        """Run the full pipeline and upload the result to S3.

        Args:
            request: VideoGenerateRequest with request_id, course_requirement,
                and student_persona.
        """
        req_id = request.request_id
        self.jobs[req_id] = {"status": "processing", "url": None}
        
        try:
            # Run the pipeline in a separate thread to avoid blocking the event loop
            # since run_pipeline is a synchronous function
            await asyncio.to_thread(
                run_pipeline, 
                request_id=req_id, 
                course_requirement=request.course_requirement, 
                student_persona=request.student_persona,
            )
            
            # Find the resulting file
            local_path = self.get_local_video_path(req_id)
            if os.path.exists(local_path):
                video_url = self.storage.upload_file(local_path)
                self.jobs[req_id] = {"status": "completed", "url": video_url}
            else:
                self.jobs[req_id] = {"status": "failed", "error": "Video file not found after execution"}
                
        except Exception as e:
            self.jobs[req_id] = {"status": "failed", "error": str(e)}

    def get_job_status(self, request_id):
        return self.jobs.get(request_id)

    def get_local_video_path(self, request_id):

        return os.path.join(get_project_dir(), "data", request_id, "video", f"final_presentation_{request_id}.mp4")