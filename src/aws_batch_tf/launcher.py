import logging
import time

from aws_batch_tf.aws.job_submitter import JobSubmitter
from aws_batch_tf.aws.messages_queue import MessagesQueue
from aws_batch_tf.launcher_settings import LauncherSettings

logger = logging.getLogger(__name__)


def launch() -> None:
    """Launch an AWS Batch job using the specified settings."""
    settings = LauncherSettings()
    if not settings.job_queue or not settings.job_definition or not settings.messages_queue_url:
        msg = "All of job_queue, job_definition, and messages_queue_url must be set in the settings."
        raise ValueError(msg)

    # Initialize AWS Batch job submitter and messages queue
    submitter = JobSubmitter(
        job_queue=settings.job_queue,
        job_definition=settings.job_definition,
        region_name=settings.region_name,
    )
    queue = MessagesQueue(url=settings.messages_queue_url, region_name=settings.region_name)

    job_id = submitter.submit(
        job_name="example-job",
        config={"EXAMPLE_ENV_VAR": "example_value"},
    )
    logger.info("Submitted job with ID: %s", job_id)

    # Poll the messages queue for a message from the job, with a timeout
    deadline = time.monotonic() + settings.poll_timeout
    while time.monotonic() < deadline:
        time.sleep(settings.poll_interval)

        messages = queue.pop()
        if messages:
            for message in messages:
                logger.info("Received message: %s", message)
            break


if __name__ == "__main__":
    launch()
