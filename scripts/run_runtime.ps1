$env:QUEUE_BACKEND = if ($env:QUEUE_BACKEND) { $env:QUEUE_BACKEND } else { "memory" }
python -m copytrading_app.workers.runtime

