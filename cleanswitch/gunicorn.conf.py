workers = 4
worker_class = 'gunicorn.workers.gthread.ThreadWorker'
threads = 3
max_requests = 1000
max_requests_jitter = 50
timeout = 120