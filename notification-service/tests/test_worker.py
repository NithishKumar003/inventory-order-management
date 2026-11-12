import json
from types import SimpleNamespace

import pytest

from app import worker


class FakeChannel:
    def __init__(self, body, publish_should_fail=False):
        self.body = body
        self.publish_should_fail = publish_should_fail
        self.callback = None
        self.published_messages = []
        self.acknowledged = []
        self.rejected = []

    def confirm_delivery(self):
        pass

    def basic_qos(self, prefetch_count):
        pass

    def basic_consume(self, queue, on_message_callback):
        self.callback = on_message_callback

    def basic_publish(
        self,
        exchange,
        routing_key,
        body,
        properties,
    ):
        if self.publish_should_fail:
            raise RuntimeError("RabbitMQ publish failed")

        self.published_messages.append({
            "queue": routing_key,
            "message": json.loads(body),
        })

    def basic_ack(self, delivery_tag):
        self.acknowledged.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.rejected.append({
            "delivery_tag": delivery_tag,
            "requeue": requeue,
        })

    def start_consuming(self):
        method = SimpleNamespace(delivery_tag=1)

        self.callback(
            self,
            method,
            None,
            self.body,
        )


class FakeConnection:
    def __init__(self, channel):
        self.fake_channel = channel
        self.is_open = True

    def channel(self):
        return self.fake_channel

    def close(self):
        self.is_open = False


@pytest.fixture
def run_worker(monkeypatch):
    def execute(message, processing_error=None, publish_should_fail=False):
        body = json.dumps(message).encode()

        channel = FakeChannel(
            body,
            publish_should_fail=publish_should_fail,
        )

        connection = FakeConnection(channel)

        monkeypatch.setattr(
            worker,
            "get_rabbitmq_connection",
            lambda: connection,
        )

        monkeypatch.setattr(
            worker,
            "declare_notification_queue",
            lambda channel: worker.MAIN_QUEUE,
        )

        def fake_process(message):
            if processing_error:
                raise processing_error

        monkeypatch.setattr(
            worker,
            "process_notification",
            fake_process,
        )

        worker.start_worker()

        return channel, connection

    return execute


def test_successful_notification_is_acknowledged(run_worker):
    channel, connection = run_worker({
        "notification_id": 101,
    })

    assert channel.acknowledged == [1]
    assert channel.published_messages == []
    assert channel.rejected == []
    assert connection.is_open is False


def test_failed_notification_is_sent_to_retry_queue(run_worker):
    channel, _ = run_worker(
        {"notification_id": 102},
        processing_error=RuntimeError("Processing failed"),
    )

    assert len(channel.published_messages) == 1

    published = channel.published_messages[0]

    assert published["queue"] == worker.RETRY_QUEUE
    assert published["message"]["notification_id"] == 102
    assert published["message"]["retry_count"] == 1
    assert channel.acknowledged == [1]


def test_notification_exceeding_retries_goes_to_dead_letter(
    run_worker,
):
    channel, _ = run_worker(
        {
            "notification_id": 103,
            "retry_count": worker.MAX_RETRIES,
        },
        processing_error=RuntimeError("Processing failed"),
    )

    assert len(channel.published_messages) == 1

    published = channel.published_messages[0]

    assert published["queue"] == worker.DEAD_LETTER_QUEUE
    assert published["message"]["notification_id"] == 103
    assert channel.acknowledged == [1]


def test_retry_publish_failure_requeues_original_message(run_worker):
    channel, _ = run_worker(
        {"notification_id": 104},
        processing_error=RuntimeError("Processing failed"),
        publish_should_fail=True,
    )

    assert channel.published_messages == []
    assert channel.acknowledged == []
    assert channel.rejected == [
        {
            "delivery_tag": 1,
            "requeue": True,
        }
    ]