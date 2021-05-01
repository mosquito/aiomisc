import asyncio
from asyncio import CancelledError, Task

import pytest

from aiomisc.service.graceful import GracefulMixin, GracefulService


async def test_graceful():
    class Graceful(GracefulMixin):
        pass

    async def pho():
        pass

    graceful = Graceful()

    task = graceful.create_graceful_task(pho())
    assert isinstance(task, Task)

    await asyncio.sleep(0.1)

    # Check that done and popped itself from the task store
    assert task.done()
    assert not graceful._GracefulMixin__tasks


@pytest.mark.parametrize(
    'sleep,timeout,error', [
        (0.2, 0.1, CancelledError),
        (0.1, 0.2, None),
    ]
)
async def test_graceful_timeout(sleep, timeout, error):
    class Graceful(GracefulMixin):
        pass

    async def pho():
        await asyncio.sleep(sleep)

    graceful = Graceful()

    task = graceful.create_graceful_task(pho())
    assert isinstance(task, Task)

    await graceful.graceful_shutdown(wait_timeout=timeout)
    assert task.done()

    if not error:
        assert not task.exception()
    else:
        with pytest.raises(error):
            assert task.exception()

    assert not graceful._GracefulMixin__tasks


@pytest.mark.parametrize(
    'cancel,error', [
        (False, None),
        (True, CancelledError),
    ]
)
async def test_graceful_shutdown(cancel, error):
    class Graceful(GracefulMixin):
        pass

    async def pho():
        await asyncio.sleep(0.1)

    graceful = Graceful()

    task = graceful.create_graceful_task(pho(), cancel=cancel)
    assert isinstance(task, Task)

    await graceful.graceful_shutdown()
    assert task.done()

    if not error:
        assert not task.exception()
    else:
        with pytest.raises(error):
            task.exception()

    assert not graceful._GracefulMixin__tasks


async def test_graceful_service():
    class TestService(GracefulService):

        task_wait = None
        task_cancel = None

        async def start(self):
            self.task_wait = self.create_graceful_task(self.pho())
            self.task_cancel = self.create_graceful_task(
                self.pho(), cancel=True,
            )

        async def pho(self):
            await asyncio.sleep(0.1)

    service = TestService()

    await service.start()
    await service.stop()

    assert service.task_wait.done()
    assert service.task_cancel.done()

    assert not service.task_wait.exception()
    with pytest.raises(CancelledError):
        assert not service.task_cancel.exception()

    assert not service._GracefulMixin__tasks


async def test_graceful_service_with_timeout_cancel():
    class TestService(GracefulService):

        graceful_wait_timeout = 0.1

        task_wait = None

        async def start(self):
            self.task_wait = self.create_graceful_task(self.pho())

        async def pho(self):
            await asyncio.sleep(0.2)

    service = TestService()

    await service.start()
    await service.stop()

    assert service.task_wait.cancelled()
    assert not service._GracefulMixin__tasks


async def test_graceful_service_with_timeout_no_cancel():
    class TestService(GracefulService):

        graceful_wait_timeout = 0.1
        cancel_on_timeout = False

        task_wait = None

        async def start(self):
            self.task_wait = self.create_graceful_task(self.pho())

        async def pho(self):
            await asyncio.sleep(0.2)
            return 123

    service = TestService()

    await service.start()
    await service.stop()

    assert not service.task_wait.done()
    assert not service._GracefulMixin__tasks

    await asyncio.sleep(0.1)

    assert service.task_wait.done()
    assert service.task_wait.result() == 123
