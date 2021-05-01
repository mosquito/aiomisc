import logging

import pkg_resources

from . import io, log
from .aggregate import aggregate
from .backoff import asyncbackoff
from .circuit_breaker import CircuitBreaker, CircuitBroken, cutout
from .context import Context, get_context
from .entrypoint import entrypoint
from .iterator_wrapper import IteratorWrapper
from .periodic import PeriodicCallback
from .pool import PoolBase
from .process_pool import ProcessPoolExecutor
from .service import Service
from .signal import Signal, receiver
from .thread_pool import (
    IteratorWrapperSeparate, ThreadPoolExecutor, context_partial,
    sync_wait_coroutine, threaded, threaded_iterable,
    threaded_iterable_separate, threaded_separate,
)
from .timeout import timeout
from .utils import (
    SelectResult, awaitable, bind_socket, cancel_tasks, chunk_list,
    new_event_loop, select, shield,
)
from .worker_pool.pool import WorkerPool

plugins = {
    entry_point.name: entry_point.load()
    for entry_point
    in pkg_resources.iter_entry_points("aiomisc.plugins")
}


def setup_plugins() -> None:
    logger = logging.getLogger(__name__)
    for name, plugin in plugins.items():
        try:
            logger.debug("Trying to load %r %r", name, plugin)
            plugin.setup()
        except:  # noqa
            logger.exception("Error on %s aiomisc plugin setup", name)
            raise


setup_plugins()


__all__ = (
    "aggregate",
    "asyncbackoff",
    "awaitable",
    "bind_socket",
    "cancel_tasks",
    "CircuitBreaker",
    "CircuitBroken",
    "chunk_list",
    "Context",
    "context_partial",
    "cutout",
    "entrypoint",
    "get_context",
    "io",
    "IteratorWrapper",
    "IteratorWrapperSeparate",
    "log",
    "new_event_loop",
    "PeriodicCallback",
    "plugins",
    "PoolBase",
    "ProcessPoolExecutor",
    "receiver",
    "select",
    "SelectResult",
    "Service",
    "shield",
    "Signal",
    "sync_wait_coroutine",
    "threaded",
    "threaded_iterable",
    "threaded_iterable_separate",
    "threaded_separate",
    "ThreadPoolExecutor",
    "timeout",
    "WorkerPool",
)
