import asyncio
import concurrent.futures
import os
import ssl
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

import aiomisc


try:
    import uvloop
except ImportError:
    uvloop = None


@pytest.fixture
def timer():
    @contextmanager
    def timer(expected_time=0, *, dispersion=0.5):
        expected_time = float(expected_time)
        dispersion_value = expected_time * dispersion

        now = time.monotonic()

        yield

        delta = time.monotonic() - now

        lower_bound = expected_time - dispersion_value
        upper_bound = expected_time + dispersion_value

        assert lower_bound < delta < upper_bound

    return timer


thread_pool_implementation = (
    concurrent.futures.ThreadPoolExecutor,
    aiomisc.ThreadPoolExecutor,
)


thread_pool_ids = (
    "default pool",
    "aiomisc pool",
)


@pytest.fixture(params=thread_pool_implementation, ids=thread_pool_ids)
def thread_pool_executor(request):
    return request.param


policies = (asyncio.DefaultEventLoopPolicy(),)
policy_ids = ("asyncio",)

if uvloop:
    policies = (uvloop.EventLoopPolicy(),) + policies
    policy_ids = ("uvloop",) + policy_ids


@pytest.fixture(params=policies, ids=policy_ids)
def event_loop_policy(request):
    return request.param


@pytest.fixture()
def certs():
    return Path(os.path.dirname(os.path.abspath(__file__))) / "certs"


@pytest.fixture(params=(ssl.Purpose.SERVER_AUTH, ssl.Purpose.CLIENT_AUTH))
def ssl_client_context(request, certs):
    ca = str(certs / "ca.pem")
    key = str(certs / "client.key")
    cert = str(certs / "client.pem")

    context = ssl.create_default_context(request.param, capath=ca)

    if key:
        context.load_cert_chain(
            cert,
            key,
        )

    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    return context
