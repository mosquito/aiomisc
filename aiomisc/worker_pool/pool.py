import asyncio
import pickle
import socket
import sys
import uuid
from functools import partial
from inspect import Traceback
from itertools import chain
from multiprocessing import AuthenticationError, ProcessError
from os import chmod, urandom
from subprocess import Popen, PIPE
from tempfile import mktemp
from typing import Optional, Set, Dict, Tuple, Any, Callable, Type, Coroutine

from aiomisc.thread_pool import threaded
from aiomisc.utils import bind_socket, cancel_tasks
from aiomisc.worker_pool.constants import (
    AddressType, INET_AF, COOKIE_SIZE,
    PacketTypes, Header, log, HASHER, T
)


class WorkerPool:
    tasks: asyncio.Queue
    server: asyncio.AbstractServer
    address: AddressType

    if hasattr(socket, "AF_UNIX"):
        def _create_socket(self) -> None:
            path = mktemp(suffix=".sock", prefix="worker-")
            self.socket = bind_socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
                address=path, port=0,
            )
            self.address = path
            chmod(path, 0o600)
    else:
        def _create_socket(self) -> None:
            self.socket = bind_socket(
                INET_AF,
                socket.SOCK_STREAM,
                address="localhost",
                port=0,
            )
            self.address = self.socket.getsockname()[:2]

    @staticmethod
    def _kill_process(process: Popen) -> None:
        if process.returncode is not None:
            return None
        process.kill()

    @threaded
    def __create_process(self, identity: str) -> Popen:
        process = Popen(
            [sys.executable, "-m", "aiomisc.worker_pool.process"],
            stdin=PIPE
        )
        self.__spawning[identity] = process

        assert process.stdin

        process.stdin.write(
            pickle.dumps((
                self.address, self.__cookie, identity
            ))
        )
        process.stdin.close()

        return process

    def __init__(
        self, workers: int, max_overflow: int = 0,
        process_poll_time: float = 0.1
    ):
        self._create_socket()
        self.__cookie = urandom(COOKIE_SIZE)
        self.__loop: Optional[asyncio.AbstractEventLoop] = None
        self.__futures: Set[asyncio.Future] = set()
        self.__spawning: Dict[str, Popen] = dict()
        self.__task_store: Set[asyncio.Task] = set()
        self.__closing = False
        self.processes: Set[Popen] = set()
        self.workers = workers
        self.tasks = asyncio.Queue(maxsize=max_overflow)
        self.process_poll_time = process_poll_time

    async def __wait_process(self, process: Popen) -> None:
        while process.poll() is None:
            await asyncio.sleep(self.process_poll_time)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self.__loop is None:
            self.__loop = asyncio.get_event_loop()
        return self.__loop

    async def __handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        async def receive() -> Tuple[PacketTypes, Any]:
            header = await reader.readexactly(Header.size)
            packet_type, payload_length = Header.unpack(header)
            payload = await reader.readexactly(payload_length)
            data = pickle.loads(payload)
            return PacketTypes(packet_type), data

        async def send(packet_type: PacketTypes, data: Any) -> None:
            payload = pickle.dumps(data)
            header = Header.pack(packet_type.value, len(payload))
            writer.write(header)
            writer.write(payload)
            await writer.drain()

        async def step(
            func: Callable, args: Tuple[Any, ...],
            kwargs: Dict[str, Any], result_future: asyncio.Future
        ) -> None:
            await send(PacketTypes.REQUEST, (func, args, kwargs))

            packet_type, result = await receive()

            if packet_type == PacketTypes.RESULT:
                result_future.set_result(result)
                return None

            if packet_type == PacketTypes.EXCEPTION:
                result_future.set_exception(result)
                return None

            raise ValueError("Unknown packet type")

        async def handler() -> None:
            log.debug("Starting to handle client")

            packet_type, salt = await receive()
            assert packet_type == PacketTypes.AUTH_SALT

            packet_type, digest = await receive()
            assert packet_type == PacketTypes.AUTH_DIGEST

            hasher = HASHER()
            hasher.update(salt)
            hasher.update(self.__cookie)

            if digest != hasher.digest():
                exc = AuthenticationError("Invalid cookie")
                await send(PacketTypes.EXCEPTION, exc)
                raise exc

            await send(PacketTypes.AUTH_OK, True)

            log.debug("Client authorized")

            packet_type, identity = await receive()
            assert packet_type == PacketTypes.IDENTITY

            process = self.__spawning.pop(identity)

            while True:
                func: Callable
                args: Tuple[Any, ...]
                kwargs: Dict[str, Any]
                result_future: asyncio.Future
                process_future: asyncio.Future

                (
                    func, args, kwargs, result_future, process_future,
                ) = await self.tasks.get()

                try:
                    if process_future.done():
                        continue

                    process_future.set_result(process)

                    if result_future.done():
                        continue

                    await step(func, args, kwargs, result_future)
                except asyncio.IncompleteReadError:
                    await self.__wait_process(process)

                    result_future.set_exception(
                        ProcessError(
                            "Process {!r} exited with code {!r}".format(
                                process, process.returncode,
                            ),
                        ),
                    )
                    break
                except Exception as e:
                    if not result_future.done():
                        self.loop.call_soon(result_future.set_exception, e)

                    if not writer.is_closing():
                        self.loop.call_soon(writer.close)

                    raise

        self.__task(handler())

    def __task(self, coroutine: Coroutine) -> asyncio.Task:
        task = self.loop.create_task(coroutine)
        task.add_done_callback(self.__task_store.remove)
        self.__task_store.add(task)
        return task

    async def start_server(self) -> None:
        self.server = await asyncio.start_server(
            self.__handle_client,
            sock=self.socket,
        )

        for n in range(self.workers):
            log.debug("Starting worker %d", n)
            await self.__spawn_process()

    def __on_exit(self, _: asyncio.Task, *, process: Popen) -> None:
        async def respawn() -> None:
            if self.__closing:
                return None

            await self.__spawn_process()
            self.processes.remove(process)

        self.__task(respawn())

    async def __spawn_process(self) -> None:
        log.debug("Spawning new process")

        identity = uuid.uuid4().hex
        process = await self.__create_process(identity)
        self.processes.add(process)

        waiter = self.__task(self.__wait_process(process))
        waiter.add_done_callback(partial(self.__on_exit, process=process))

    def __create_future(self) -> asyncio.Future:
        future = self.loop.create_future()
        self.__futures.add(future)
        future.add_done_callback(self.__futures.remove)
        return future

    def __reject_futures(self) -> None:
        for future in self.__futures:
            if future.done():
                continue
            future.set_exception(RuntimeError("Pool closed"))

    async def close(self) -> None:
        self.__closing = True

        await cancel_tasks(
            chain(tuple(self.__task_store), tuple(self.__futures))
        )

        while self.processes:
            self._kill_process(self.processes.pop())

    async def create_task(
        self, func: Callable[..., T],
        *args: Any, **kwargs: Any
    ) -> T:
        result_future = self.__create_future()
        process_future = self.__create_future()

        await self.tasks.put((
            func, args, kwargs, result_future, process_future,
        ))

        process: Popen = await process_future

        try:
            return await result_future
        except asyncio.CancelledError:
            self._kill_process(process)
            raise

    async def __aenter__(self) -> "WorkerPool":
        await self.start_server()
        return self

    async def __aexit__(
        self, exc_type: Type[Exception],
        exc_val: Exception, exc_tb: Traceback
    ) -> None:
        await self.close()
