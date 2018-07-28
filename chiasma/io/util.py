import time
from typing import TypeVar, Callable

from amino import do, Do

from chiasma.io.compute import TmuxIO

A = TypeVar('A')


@do(TmuxIO[A])
def tmuxio_repeat_timeout(
        thunk: Callable[[], TmuxIO[A]],
        check: Callable[[A], bool],
        error: str,
        timeout: float,
        interval: float=None,
) -> Do:
    effective_interval = .01 if interval is None else interval
    start = yield TmuxIO.simple(time.time)
    @do(TmuxIO[None])
    def wait_and_recurse() -> Do:
        yield TmuxIO.sleep(effective_interval)
        yield recurse()
    @do(TmuxIO[None])
    def recurse() -> Do:
        result = yield thunk()
        done = check(result)
        yield (
            TmuxIO.pure(result)
            if done else
            TmuxIO.error(error)
            if time.time() - start > timeout else
            wait_and_recurse()
        )
    yield recurse()


__all__ = ('tmuxio_repeat_timeout',)
