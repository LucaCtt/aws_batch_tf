import boto3


class JobSubmitter:
    """Submits jobs as AWS Batch."""

    def __init__(self, job_queue: str, job_definition: str, region_name: str) -> None:
        """Initialize the submitter with AWS Batch client and job configuration.

        Arguments:
            job_queue (str): The name of the AWS Batch job queue to submit jobs to.
            job_definition (str): The name of the AWS Batch job definition to use for submitted jobs.
            region_name (str): The AWS region where the Batch service is located.

        """
        self.__batch_client = boto3.client("batch", region_name=region_name)
        self.__job_queue = job_queue
        self.__job_definition = job_definition

    def submit(self, job_name: str, config: dict) -> str:
        """Submit a job to AWS Batch with the given environment variables.

        Arguments:
            job_name (str): The name of the job to submit.
            config (dict): A dictionary of environment variables to pass to the job.

        Returns:
            str: The ID of the submitted job.

        """
        response = self.__batch_client.submit_job(
            jobName=job_name,
            jobQueue=self.__job_queue,
            jobDefinition=self.__job_definition,
            containerOverrides={
                "environment": [{"name": k, "value": str(v)} for k, v in config.items() if v is not None],
            },
        )
        return response["jobId"]

    def terminate(self, job_id: str, reason: str | None = None) -> None:
        """Terminate a running AWS Batch job.

        Arguments:
            job_id (str): The ID of the job to terminate.
            reason (str, optional): The reason for termination. Defaults to None.

        """
        self.__batch_client.terminate_job(jobId=job_id, reason=reason or "Terminated by JobSubmitter")
