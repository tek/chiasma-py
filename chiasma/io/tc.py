import abc
from typing import TypeVar, Callable, Generic

from amino.tc.base import ImplicitInstances, TypeClass, tc_prop
from amino.lazy import lazy
from amino.tc.monad import Monad
from amino import Either, IO, Maybe
from amino.state import tcs, StateT, State, EitherState
from amino.func import CallByName

from chiasma.io.compute import TmuxIO
from chiasma.io.trace import cframe
from chiasma.tmux import Tmux

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
S = TypeVar('S')


class TmuxIOInstances(ImplicitInstances):

    @lazy
    def _instances(self) -> 'amino.map.Map':
        from amino.map import Map
        return Map({Monad: TmuxIOMonad()})


class TmuxIOMonad(Monad, tpe=TmuxIO):

    def pure(self, a: A) -> TmuxIO[A]:
        return TmuxIO.pure(a)

    def flat_map(self, fa: TmuxIO[A], f: Callable[[A], TmuxIO[B]]) -> TmuxIO[B]:
        return fa.flat_map(f)


class TmuxIOState(Generic[S, A], StateT[TmuxIO, S, A], tpe=TmuxIO):

    @staticmethod
    def io(f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    @staticmethod
    def delay(f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    @staticmethod
    def suspend(f: Callable[[Tmux], TmuxIO[A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.suspend(f))

    @staticmethod
    def from_io(io: IO[A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.wrap_either(lambda v: io.attempt))

    @staticmethod
    def from_id(st: State[S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.pure(s.value))

    @staticmethod
    def from_either_state(st: EitherState[S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.from_either(s))

    @staticmethod
    def from_either(e: Either[str, A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.from_either(e))

    @staticmethod
    def from_maybe(m: Maybe[A], error: CallByName) -> 'TmuxIOState[S, A]':
        return TmuxIOState.from_either(m.to_either(error))

    @staticmethod
    def failed(e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.failed(e))

    @staticmethod
    def error(e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.error(e))

    @staticmethod
    def inspect_either(f: Callable[[S], Either[str, A]]) -> 'TmuxIOState[S, A]':
        frame = cframe()
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_either(f(s), frame))

    @staticmethod
    def read(cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.read(cmd, *args))

    @staticmethod
    def write(cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.write(cmd, *args))


tcs(TmuxIO, TmuxIOState)
TS = TmuxIOState


class ToTmuxIOState(TypeClass):

    @abc.abstractproperty
    def tmux(self) -> TS:
        ...


class IdStateToTmuxIOState(ToTmuxIOState, tpe=State):

    @tc_prop
    def tmux(self, fa: State[S, A]) -> TS[S, A]:
        return TmuxIOState.from_id(fa)


class EitherStateToTmuxIOState(ToTmuxIOState, tpe=EitherState):

    @tc_prop
    def tmux(self, fa: EitherState[S, A]) -> TS:
        return TmuxIOState.from_either_state(fa)


class TmuxIOToTmuxIOState(ToTmuxIOState, tpe=TmuxIO):

    @tc_prop
    def tmux(self, fa: TmuxIO[A]) -> TS[S, A]:
        return TS.lift(fa)

    @tc_prop
    def state(self, fa: TmuxIO[A]) -> TS[S, A]:
        return self.tmux(fa)


__all__ = ('TmuxIOInstances', 'TmuxIOState', 'TS', 'ToTmuxIOState')
