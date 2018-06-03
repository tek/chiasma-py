import abc
import time
import inspect
from traceback import FrameSummary
from typing import TypeVar, Callable, Any, Generic, Union, Tuple

from amino.tc.base import F, ImplicitsMeta
from amino import Either, __, IO, Maybe, Left, Eval, List, Right, Lists, options, Nil, Just, Do, L, Nothing
from amino.func import CallByName, tailrec
from amino.do import do
from amino.dat import ADT, ADTMeta

from chiasma.tmux import Tmux, TmuxCmd, TmuxCmdResult, TmuxCmdSuccess, TmuxCmdError
from chiasma.io.data import TSuccess, TError, TFatal, TResult
from chiasma.io.trace import TmuxIOException

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
S = TypeVar('S')


class TmuxIOMeta(ADTMeta, ImplicitsMeta):

    @property
    def unit(self) -> 'TmuxIO[A]':
        return self.pure(None)


class TmuxIO(Generic[A], F[A], ADT['TmuxIO[A]'], implicits=True, auto=True, metaclass=TmuxIOMeta):
    debug = options.io_debug.exists

    @staticmethod
    def wrap_either(f: Callable[[Tmux], Either[B, A]], frame: FrameSummary=None) -> 'TmuxIO[A]':
        return TmuxIO.suspend(lambda a: f(a).cata(TmuxIO.error, TmuxIO.pure), _frame=frame)

    @staticmethod
    def from_either(e: Either[str, A], frame: FrameSummary=None) -> 'TmuxIO[A]':
        return TmuxIO.wrap_either(lambda v: e, frame)

    @staticmethod
    def from_maybe(e: Maybe[A], error: CallByName) -> 'TmuxIO[A]':
        return TmuxIO.from_either(e.to_either(error))

    @staticmethod
    def exception(exc: Exception) -> 'TmuxIO[A]':
        return TmuxIOFatal(exc)

    @staticmethod
    def failed(msg: str) -> 'TmuxIO[A]':
        return TmuxIO.exception(Exception(msg))

    @staticmethod
    def error(msg: str) -> 'TmuxIO[A]':
        return TmuxIOError(msg)

    @staticmethod
    def from_io(io: IO[A]) -> 'TmuxIO[A]':
        return TmuxIO.delay(lambda a: io.attempt.get_or_raise())

    @staticmethod
    def delay(f: Callable[..., A], *a: Any, **kw: Any) -> 'TmuxIO[A]':
        def g(tmux: Tmux) -> A:
            return Pure(f(tmux, *a, **kw))
        return Suspend(g)

    @staticmethod
    def simple(f: Callable[..., A], *a, **kw) -> 'TmuxIO[A]':
        return TmuxIO.delay(lambda v: f(*a, **kw))

    @staticmethod
    def suspend(f: Callable[..., 'TmuxIO[A]'], *a: Any, _frame: FrameSummary=None, **kw: Any) -> 'TmuxIO[A]':
        def g(tmux: Tmux) -> TmuxIO[A]:
            return f(tmux, *a, **kw)
        return Suspend(g, _frame)

    @staticmethod
    def pure(a: A) -> 'TmuxIO[A]':
        return Pure(a)

    @staticmethod
    def write(cmd: str, *args: str) -> 'TmuxIO[A]':
        return TmuxWrite(TmuxCmd(cmd, Lists.wrap(args)))

    @staticmethod
    def read(cmd: str, *args: str) -> 'TmuxIO[A]':
        return TmuxRead(TmuxCmd(cmd, Lists.wrap(args)))

    @staticmethod
    @do(IO[Tuple['TmuxIO', A]])
    def to_io(fa: 'TmuxIO[A]', tmux: Tmux) -> Do:
        result = yield IO.delay(fa.run, tmux)
        yield IO.from_either(result.to_either)

    @staticmethod
    def sleep(duration: float) -> 'TmuxIO[None]':
        return TmuxIO.delay(lambda v: time.sleep(duration))

    @staticmethod
    def flush() -> 'TmuxIO[None]':
        return TmuxIO.read('list-clients').void

    @abc.abstractmethod
    def _flat_map(self, f: Callable[[A], 'TmuxIO[B]'], ts: Eval[str], fs: Eval[str]) -> 'TmuxIO[B]':
        ...

    @abc.abstractmethod
    def step(self, tmux: Tmux) -> 'TmuxIO[A]':
        ...

    def __init__(self, frame: FrameSummary=None) -> None:
        self.frame = frame or inspect.currentframe()

    def flat_map(self, f: Callable[[A], 'TmuxIO[B]']) -> 'TmuxIO[B]':
        return self._flat_map(f)

    def run(self, tmux: Tmux) -> A:
        @tailrec
        def run(t: 'TmuxIO[A]', writes: List[TmuxCmd]=Nil) -> Tuple[bool, Union[A, 'TmuxIO[A]']]:
            if isinstance(t, (Suspend, BindSuspend)):
                return True, (t.step(tmux), writes)
            elif isinstance(t, ScheduleWrite):
                return True, (t.next(None), writes.cat(t.cmd))
            elif isinstance(t, ExecuteRead):
                a = execute_read(writes, t.cmd)
                return True, (a.flat_map(t.next), Nil)
            elif isinstance(t, TmuxWrite):
                a = execute_write(t.cmd)
                return True, (a, Nil)
            elif isinstance(t, TmuxRead):
                a = execute_read(Nil, t.cmd)
                return True, (a, Nil)
            elif isinstance(t, Pure) and writes.empty:
                return False, TSuccess(t.value)
            elif isinstance(t, Pure):
                a = execute_writes(writes)
                return True, (a.and_then(t), Nil)
            elif isinstance(t, TmuxIOError):
                return False, TError(t.error)
            elif isinstance(t, TmuxIOFatal):
                return False, TFatal(t.exception)
            else:
                raise Exception(f'got invalid TmuxIO computation step result {t}')
        return run(self)

    def result(self, tmux: Tmux) -> TResult[A]:
        try:
            return self.run(tmux)
        except TmuxIOException as e:
            return TFatal(e)

    def either(self, tmux: Tmux) -> Either[TmuxIOException, A]:
        try:
            return self.run(tmux).to_either
        except TmuxIOException as e:
            return Left(e)

    def attempt(self, tmux: Tmux) -> Either[TmuxIOException, A]:
        return self.either(tmux)

    def unsafe(self, tmux: Tmux) -> A:
        return self.either(tmux).get_or_raise()

    def recover(self, f: Callable[[Exception], A]) -> 'TmuxIO[A]':
        return TmuxIO.delay(self.attempt).map(__.value_or(f))

    def recover_error(self, f: Callable[[str], A]) -> 'TmuxIO[A]':
        def recover(r: TResult[A]) -> TmuxIO[A]:
            return (
                TmuxIO.pure(f(r.error))
                if isinstance(r, TError) else
                TmuxIO.exception(r.exception)
                if isinstance(r, TFatal) else
                TmuxIO.pure(r.value)
            )
        return TmuxIO.delay(self.result).flat_map(recover)

    # def recover_error_with(self, f: Callable[[str], 'TmuxIO[A]']) -> 'TmuxIO[A]':
    #     def recover(r: TResult[A]) -> TmuxIO[A]:
    #         return (
    #             f(r.error)
    #             if isinstance(r, TError) else
    #             r
    #         )
    #     return TmuxIO.delay(self.result).flat_map(recover)

    @do('TmuxIO[A]')
    def ensure(self, f: Callable[[Either[Exception, A]], 'TmuxIO[None]']) -> Do:
        result = yield TmuxIO.delay(self.attempt)
        yield f(result)
        yield TmuxIO.from_either(result)

    def effect(self, f: Callable[[A], Any]) -> 'TmuxIO[A]':
        def wrap(v: Tmux) -> A:
            ret = self.run(v)
            f(ret)
            return ret
        return TmuxIO.delay(wrap)

    __mod__ = effect

    def error_effect(self, f: Callable[[Exception], None]) -> 'TmuxIO[A]':
        return self.ensure(lambda a: TmuxIO.delay(lambda v: a.leffect(f)))

    def error_effect_f(self, f: Callable[[Exception], 'TmuxIO[None]']) -> 'TmuxIO[A]':
        return self.ensure(lambda a: TmuxIO.suspend(lambda v: a.cata(f, TmuxIO.pure)))


class Suspend(Generic[A], TmuxIO[A]):

    def __init__(
            self,
            thunk: Callable[[Tmux], TmuxIO[A]],
            frame: FrameSummary=None,
    ) -> None:
        super().__init__(frame)
        self.thunk = thunk

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        try:
            return self.thunk(tmux)
        except TmuxIOException as e:
            raise e
        except Exception as e:
            raise TmuxIOException('', Nil, e, self.frame)

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return BindSuspend(self.thunk, f, self.frame)


class BindSuspend(Generic[A, B], TmuxIO[B]):

    def __init__(
            self,
            thunk: Callable[[Tmux], TmuxIO[A]],
            f: Callable[[A], TmuxIO[B]],
            frame: FrameSummary=None,
    ) -> None:
        super().__init__(frame)
        self.thunk = thunk
        self.f = f

    def step(self, tmux: Tmux) -> TmuxIO[B]:
        try:
            step = self.thunk(tmux)
        except TmuxIOException as e:
            raise e
        except Exception as e:
            raise TmuxIOException('', Nil, e, self.frame)
        if isinstance(step, TmuxWrite):
            return ScheduleWrite(step.cmd, self.f)
        if isinstance(step, TmuxRead):
            return ExecuteRead(step.cmd, self.f)
        else:
            try:
                return step.flat_map(self.f)
            except TmuxIOException as e:
                raise e
            except Exception as e:
                raise TmuxIOException('', Nil, e, step.frame)

    def _flat_map(self, f: Callable[[B], TmuxIO[C]]) -> TmuxIO[C]:
        def bs(tmux: Tmux) -> TmuxIO[C]:
            return BindSuspend(self.thunk, lambda a: self.f(a).flat_map(f), self.frame)
        return Suspend(bs)


class Pure(Generic[A], TmuxIO[A]):

    def __init__(self, value: A) -> None:
        super().__init__(Nil)
        self.value = value

    def _arg_desc(self) -> List[str]:
        return List(str(self.value))

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        def g(tmux: Tmux) -> TmuxIO[B]:
            return f(self.value)
        return Suspend(g, Nil)


class TmuxIOCmd(Generic[A], TmuxIO[A]):

    def __init__(self, cmd: TmuxCmd) -> None:
        super().__init__(Nil)
        self.cmd = cmd

    def _arg_desc(self) -> List[str]:
        return self.cmd._arg_desc()


class TmuxWrite(Generic[A], TmuxIOCmd[A]):

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return BindSuspend(lambda t: self, f, self.frame)


class TmuxRead(Generic[A], TmuxIOCmd[A]):

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return BindSuspend(lambda t: self, f, self.frame)


class ScheduleWrite(Generic[A], TmuxIO[A]):

    def __init__(self, cmd: TmuxCmd, next: Callable[[None], TmuxIO[A]]) -> None:
        self.cmd = cmd
        self.next = next

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return self


class ExecuteRead(Generic[A], TmuxIO[A]):

    def __init__(self, cmd: TmuxCmd, next: Callable[[List[str]], TmuxIO[A]]) -> None:
        self.cmd = cmd
        self.next = next

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return self


class TmuxIOError(Generic[A], TmuxIO[A]):

    def __init__(self, error: str) -> None:
        self.error = error

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return self

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self


class TmuxIOFatal(Generic[A], TmuxIO[A]):

    def __init__(self, exception: Exception) -> None:
        self.exception = exception

    def _flat_map(self, f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return self

    def step(self, tmux: Tmux) -> TmuxIO[A]:
        return self


@do(TmuxIO[List[TmuxCmdResult]])
def execute_cmds(writes: List[TmuxCmd], read: Maybe[TmuxCmd]) -> Do:
    cmds = writes.cat_m(read)
    yield TmuxIO.delay(__.execute_cmds(cmds))


def read_result(result: TmuxCmdResult) -> Either[List[str], List[str]]:
    return (
        Right(result.output.output)
        if isinstance(result, TmuxCmdSuccess) else
        Left(result.output.output.cons(f'tmux command {result.cmd} failed:'))
        if isinstance(result, TmuxCmdError) else
        Left(result.output.output.cons(f'fatal tmux command execution in {result.cmds}:'))
    )


@do(TmuxIO[Either[List[str], List[str]]])
def execute_read(writes: List[TmuxCmd], read: TmuxCmd) -> Do:
    results = yield execute_cmds(writes, Just(read))
    yield TmuxIO.from_either(results.last.map(read_result) | L(Left)(f'no output for {read}'))


@do(TmuxIO[Either[List[str], List[str]]])
def execute_writes(writes: List[TmuxCmd]) -> Do:
    results = yield execute_cmds(writes, Nothing)
    yield TmuxIO.from_either(results.traverse(read_result, Either).map(lambda a: a.last | Nil))


def execute_write(write: TmuxCmd) -> TmuxIO[Either[List[str], List[str]]]:
    return execute_writes(List(write))


__all__ = ('TmuxIO',)
