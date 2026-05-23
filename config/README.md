# Project Pipeline Settings

`pipeline_parallelism.json` keeps shared local defaults for long-running page
processing workflows:

- `max_parallel_opencv_tasks` - how many OpenCV page-layout jobs may run at once.
- `max_parallel_ocr_tasks` - how many OCR jobs may run at once.
- `tesseract_threads_per_process` - `OMP_THREAD_LIMIT` for each Tesseract process.

Command-line parameters still override these defaults for one-off runs.
