from pathlib import Path
import collections
import contextlib
import cProfile
import datetime
import time

import pytest

from . import common


tool_conf = common.get_conf().get('tool', {}).get('hat-doit', {})
durations = collections.deque()
profile_dir = Path(tool_conf.get('pytest_profile_dir', 'build/profile'))


def pytest_addoption(parser):
    parser.addoption("--unit",
                     action="store_true",
                     help="run unit tests")
    parser.addoption("--sys",
                     action="store_true",
                     help="run system tests")
    parser.addoption("--perf",
                     action="store_true",
                     help="run performance tests")


def pytest_configure(config):
    with contextlib.suppress(ImportError):
        import hat.aio
        hat.aio.init_asyncio()

    config.addinivalue_line("markers", "unit: mark unit test")
    config.addinivalue_line("markers", "sys: mark system test")
    config.addinivalue_line("markers", "perf: mark performance test")


def pytest_runtest_setup(item):
    options = {option for option in ['unit', 'sys', 'perf']
               if item.config.getoption(f'--{option}')}
    if not options:
        options.add('unit')

    marks = {mark for mark in ['unit', 'sys', 'perf']
             if any(item.iter_markers(name=mark))}
    if not marks:
        marks.add('unit')

    if options.isdisjoint(marks):
        pytest.skip("test not marked for execution")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not durations:
        return

    terminalreporter.write('\nDuration report:\n')
    for i in durations:
        identifier = i['identifier']
        description = i['description']
        dt = datetime.timedelta(seconds=i['dt'])
        terminalreporter.write(f"> {dt} [{identifier}] {description}\n")


@pytest.fixture
def duration(request):
    identifier = request.module.__name__
    if request.cls:
        identifier += f"::{request.cls.__name__}"
    if request.function:
        identifier += f"::{request.function.__name__}"

    @contextlib.contextmanager
    def duration(description):
        start = time.monotonic()
        yield
        dt = time.monotonic() - start
        durations.append({'identifier': identifier,
                          'description': description,
                          'dt': dt})

    return duration


@pytest.fixture
def profile(request):

    @contextlib.contextmanager
    def profile(name=None):
        with cProfile.Profile() as pr:
            yield

        suffix = f'.{name}.prof' if name else '.prof'
        path = (profile_dir /
                Path(*request.module.__name__.split('.')) /
                request.function.__name__).with_suffix(suffix)

        path.parent.mkdir(parents=True, exist_ok=True)
        pr.dump_stats(str(path))

    return profile
