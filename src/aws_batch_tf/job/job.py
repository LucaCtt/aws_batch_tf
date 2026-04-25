from aws_batch_tf.aws.messages_queue import MessagesQueue
from aws_batch_tf.job.job_settings import JobSettings


def job() -> None:
    """Run the job."""
    settings = JobSettings()
    if settings.messages_queue_url is None:
        msg = "No messages queue URL provided. Skipping message sending."
        raise ValueError(msg)

    messages_queue = MessagesQueue(url=settings.messages_queue_url, region_name=settings.region_name)
    messages_queue.push({"status": "OK", "message": "Hello from AWS Batch!"})


if __name__ == "__main__":
    job()
