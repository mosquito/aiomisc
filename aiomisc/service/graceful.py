import asyncio
import logging

try:
    from asyncio import create_task
except ImportError:
    from asyncio import ensure_future as create_task    # type: ignore
from asyncio import Task
from typing import Coroutine, Dict, Optional

from . import Service
from ..timeout import timeout, Number

log = logging.getLogger(__name__)


class GracefulMixin:

    __tasks: Dict[Task, bool] = {}

    def create_graceful_task(
            self, coro: Coroutine, *, cancel: bool = False,
    ) -> Task:
        """
        Creates a task that will either be awaited or cancelled and awaited
        upon service stop.
        :param coro:
        :param cancel: whether to cancel or await the task on service stop
        (default `False`)
        :return: created task
        """
        task = create_task(coro)
        # __tasks may be cleared before the task finishes
        task.add_done_callback(lambda task: self.__tasks.pop(task, None))
        self.__tasks[task] = cancel
        return task

    async def graceful_shutdown(
            self, *,
            wait_timeout: Number = None,
            cancel_on_timeout: bool = True,
    ) -> None:
        if self.__tasks:
            items = list(self.__tasks.items())
            to_cancel = [task for task, cancel in items if cancel]
            to_wait = [task for task, cancel in items if not cancel]

            log.info(
                'Graceful shutdown: cancel %d and wait for %d tasks',
                len(to_cancel), len(to_wait)
            )

            await asyncio.wait([
                self.__cancel_tasks(*to_cancel),
                self.__finish_tasks(
                    *to_wait,
                    wait_timeout=wait_timeout,
                    cancel_on_timeout=cancel_on_timeout,
                )
            ])

            self.__tasks.clear()

    async def __cancel_tasks(self, *tasks: Task) -> None:
        await self.__wait_tasks(*tasks, cancel=True)

    async def __finish_tasks(
            self, *tasks: Task,
            wait_timeout: Optional[Number],
            cancel_on_timeout: bool,
    ) -> None:

        if wait_timeout is None:
            await self.__wait_tasks(*tasks, cancel=False)
            return

        try:
            await timeout(wait_timeout)(self.__wait_tasks)(
                *tasks, cancel=False,
            )
        except asyncio.TimeoutError:
            log.info('Graceful shutdown: wait timeouted')
            if not cancel_on_timeout:
                return

            to_cancel = [task for task in tasks if not task.done()]
            log.info(
                'Graceful shutdown: cancel %d tasks after timeout',
                len(to_cancel),
            )
            for task in to_cancel:
                task.cancel()

    @staticmethod
    async def __wait_tasks(*tasks: Task, cancel: bool) -> None:
        if not tasks:
            return

        to_stop = []

        for task in tasks:
            if task.done():
                continue

            if cancel:
                task.cancel()

            to_stop.append(task)

        await asyncio.wait(to_stop)


class GracefulService(Service, GracefulMixin):

    graceful_wait_timeout = None  # type: float # in seconds
    cancel_on_timeout = True  # type: bool

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self, exception: Exception = None) -> None:
        await self.graceful_shutdown(
            wait_timeout=self.graceful_wait_timeout,
            cancel_on_timeout=self.cancel_on_timeout,
        )
