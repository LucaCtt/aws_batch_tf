import json

import boto3


class MessagesQueue:
    """AWS SQS-backed message queue with retry logic for transient errors."""

    def __init__(self, url: str, region_name: str) -> None:
        """Initialize the MessagesQueue.

        Arguments:
            url (str): SQS queue URL.
            region_name (str): AWS region for the SQS client.

        """
        self._sqs = boto3.client("sqs", region_name=region_name)
        self._url = url

    @property
    def url(self) -> str:
        """The SQS queue URL. Raises QueueNotCreatedError if not yet created."""
        return self._url

    def push(self, item: dict) -> None:
        """Push a message onto the queue.

        Arguments:
            item: The message body to send, which will be JSON-encoded before sending.

        """
        self._sqs.send_message(QueueUrl=self.url, MessageBody=json.dumps(item))

    def pop(
        self,
        max_messages: int = 10,
        filter_values: dict | None = None,
        delete_non_matching: bool = True,
    ) -> list[dict]:
        """Pop up to max_messages messages, deleting each only after it is read.

        Arguments:
            max_messages (int): Maximum number of messages to retrieve.
            filter_values (dict | None): Optional dictionary of values to filter messages. Only messages for which
                all keys match their corresponding values will be included in the results and deleted from the queue.
            delete_non_matching (bool): If True, messages that do not match the filter
                will also be deleted from the queue.

        Returns:
            List of decoded message bodies.

        """
        results = []
        remaining = max_messages

        while remaining > 0:
            messages = self._receive(min(remaining, 10))
            if not messages:
                break

            for msg in messages:
                body = json.loads(msg["Body"])
                if filter_values is None or all(
                    body.get(k) == v for k, v in filter_values.items()
                ):
                    results.append(body)
                    self._delete(msg["ReceiptHandle"])
                elif delete_non_matching:
                    self._delete(msg["ReceiptHandle"])

            remaining -= len(messages)

        return results

    def _receive(self, count: int) -> list[dict]:
        return self._sqs.receive_message(
            QueueUrl=self._url,
            MaxNumberOfMessages=count,
        ).get("Messages", [])

    def _delete(self, receipt_handle: str) -> None:
        self._sqs.delete_message(QueueUrl=self._url, ReceiptHandle=receipt_handle)
