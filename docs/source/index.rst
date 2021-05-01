aiomisc - miscellaneous utils for asyncio
=========================================

.. image:: https://coveralls.io/repos/github/mosquito/aiomisc/badge.svg?branch=master
   :target: https://coveralls.io/github/mosquito/aiomisc
   :alt: Coveralls

.. image:: https://github.com/aiokitchen/aiomisc/workflows/tox/badge.svg
   :target: https://github.com/aiokitchen/aiomisc/actions?query=workflow%3Atox
   :alt: Actions

.. image:: https://img.shields.io/pypi/v/aiomisc.svg
   :target: https://pypi.python.org/pypi/aiomisc/
   :alt: Latest Version

.. image:: https://img.shields.io/pypi/wheel/aiomisc.svg
   :target: https://pypi.python.org/pypi/aiomisc/

.. image:: https://img.shields.io/pypi/pyversions/aiomisc.svg
   :target: https://pypi.python.org/pypi/aiomisc/

.. image:: https://img.shields.io/pypi/l/aiomisc.svg
   :target: https://pypi.python.org/pypi/aiomisc/


Miscellaneous utils for asyncio.


Installation
------------

Installing from pypi:

.. code-block:: bash

    pip3 install aiomisc

With uvloop_:

.. code-block:: bash

    pip3 install "aiomisc[uvloop]"


With aiohttp_:

.. code-block:: bash

    pip3 install "aiomisc[aiohttp]"


Installing from github.com:

.. code-block:: bash

    pip3 install git+https://github.com/mosquito/aiomisc.git


.. _uvloop: https://pypi.org/project/uvloop
.. _aiohttp: https://pypi.org/project/aiohttp


Quick Start
-----------

Async entrypoint with logging and useful arguments:

.. code-block:: python

    import argparse
    import asyncio
    import os
    import logging

    from aiomisc import entrypoint


    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-L", "--log-level", help="Log level",
        default=os.getenv('LOG_LEVEL', 'info'),
        choices=(
            'critical', 'fatal', 'error', 'warning',
            'warn', 'info', 'debug', 'notset'
        ),
    )

    parser.add_argument(
        "--log-format", help="Log format",
        default=os.getenv('LOG_FORMAT', 'color'),
        choices=aiomisc.log.LogFormat.choices(),
        metavar='LOG_FORMAT',
    )

    parser.add_argument(
        "-D", "--debug", action='store_true',
        help="Run loop and application in debug mode"
    )


    parser.add_argument(
        "--pool-size", help="Thread pool size",
        default=os.getenv('THREAD_POOL'), type=int,
    )


    log = logging.getLogger(__name__)


    async def main():
        log.info('Starting')
        await asyncio.sleep(3)
        log.info('Exiting')


    if __name__ == '__main__':
        arg = parser.parse_args()

        with entrypoint(log_level=arg.log_level,
                        log_format=arg.log_format) as loop:
            loop.run_until_complete(main())


Install event loop on program start:

.. code-block:: python

    import asyncio
    import aiomisc


    # Installing uvloop event loop
    # and set `aiomisc.thread_pool.ThreadPoolExecutor`
    # as default executor
    aiomisc.new_event_loop()


    async def main():
        await asyncio.sleep(3)


    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())


Close current event loop and install a new one:

.. code-block:: python

    import asyncio
    import aiomisc


    async def main():
        await asyncio.sleep(3)


    if __name__ == '__main__':
        loop = aiomisc.new_event_loop()
        loop.run_until_complete(main())

Table Of Contents
+++++++++++++++++

.. toctree::
   :glob:
   :maxdepth: 3

   entrypoint
   services
   pool
   context
   timeout
   async_backoff
   circuit_breaker
   aggregate
   io
   threads
   process_pool
   utils
   worker_pool
   logging
   pytest
   signal
   plugins
   apidoc

Versioning
----------

This software follows `Semantic Versioning`_


How to develop?
---------------

Should be installed:

* `virtualenv`
* GNU Make as `make`
* Python 3.5+ as `python3`


For setting up developer environment just type

    .. code-block::

        make develop


.. _Semantic Versioning: http://semver.org/
