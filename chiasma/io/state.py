from typing import Generic, TypeVar, Callable, Tuple, cast, Type, Any

from lenses import UnboundLens

from amino.tc.base import ImplicitsMeta, Implicits
from amino.tc.monad import Monad
from amino.tc.zip import Zip
from amino.instances.list import ListTraverse
from amino import List, curried
from amino.util.string import ToStr
from amino.state.base import StateT
from chiasma.io.compute import TmuxIO

import abc
from amino.tc.base import TypeClass, tc_prop
from amino.state import State, EitherState
from chiasma.tmux import Tmux
from amino import IO, Maybe, Either
from amino.func import CallByName
E = TypeVar('E')

A = TypeVar('A')
B = TypeVar('B')
S = TypeVar('S')
R = TypeVar('R')
ST1 = TypeVar('ST1')


monad: Monad = cast(Monad, Monad.fatal(TmuxIO))


class TmuxIOStateCtor(Generic[S]):

    def inspect(self, f: Callable[[S], A]) -> 'TmuxIOState[S, A]':
        def g(s: S) -> TmuxIO[Tuple[S, A]]:
            return monad.pure((s, f(s)))
        return TmuxIOState.apply(g)

    def inspect_f(self, f: Callable[[S], TmuxIO[A]]) -> 'TmuxIOState[S, A]':
        def g(s: S) -> TmuxIO[Tuple[S, A]]:
            return f(s).map(lambda a: (s, a))
        return TmuxIOState.apply(g)

    def pure(self, a: A) -> 'TmuxIOState[S, A]':
        return TmuxIOState.apply(lambda s: monad.pure((s, a)))

    def delay(self, fa: Callable[..., A], *a: Any, **kw: Any) -> 'TmuxIOState[S, A]':
        return TmuxIOState.apply(lambda s: monad.pure((s, fa(*a, **kw))))

    def lift(self, fa: TmuxIO[A]) -> 'TmuxIOState[S, A]':
        def g(s: S) -> TmuxIO[Tuple[S, A]]:
            return fa.map(lambda a: (s, a))
        return TmuxIOState.apply(g)

    def modify(self, f: Callable[[S], S]) -> 'TmuxIOState[S, None]':
        return TmuxIOState.apply(lambda s: monad.pure((f(s), None)))

    def modify_f(self, f: Callable[[S], TmuxIO[S]]) -> 'TmuxIOState[S, None]':
        return TmuxIOState.apply(lambda s: f(s).map(lambda a: (a, None)))

    def get(self) -> 'TmuxIOState[S, S]':
        return self.inspect(lambda a: a)

    @property
    def unit(self) -> 'TmuxIOState[S, None]':
        return TmuxIOState.pure(None)

    def io(self, f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    def delay(self, f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    def suspend(self, f: Callable[[Tmux], TmuxIO[A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.suspend(f))

    def from_io(self, io: IO[A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.wrap_either(lambda v: io.attempt))

    def from_id(self, st: State[S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.pure(s.value))

    def from_maybe(self, a: Maybe[B], err: CallByName) -> 'TmuxIOState[S, B]':
        return TmuxIOState.lift(TmuxIO.from_maybe(a, err))

    m = from_maybe

    def from_either(self, e: Either[str, A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.from_either(e))

    e = from_either

    def from_either_state(self, st: EitherState[E, S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.from_either(s))

    def failed(self, e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.failed(e))

    def error(self, e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.error(e))

    def inspect_maybe(self, f: Callable[[S], Maybe[A]], err: CallByName) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_maybe(f(s), err))

    def inspect_either(self, f: Callable[[S], Either[str, A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_either(f(s)))

    def simple(self, f: Callable[..., A], *a: Any, **kw: Any) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.simple(f, *a, **kw))

    def sleep(self, duration: float) -> 'TmuxIOState[S, None]':
        return TS.lift(TmuxIO.sleep(duration))

    def modify_e(self, f: Callable[[S], Either[str, S]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_either(f).flat_map(TmuxIOState.set)

    def read(self, cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.read(cmd, *args))

    def write(self, cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.write(cmd, *args))


class TmuxIOStateMeta(ImplicitsMeta):

    def cons(self, run_f: TmuxIO[Callable[[S], TmuxIO[Tuple[S, A]]]]) -> 'TmuxIOState[S, A]':
        return self(run_f)

    def apply(self, f: Callable[[S], TmuxIO[Tuple[S, A]]]) -> 'TmuxIOState[S, A]':
        return self.cons(monad.pure(f))

    def apply_f(self, run_f: TmuxIO[Callable[[S], TmuxIO[Tuple[S, A]]]]) -> 'TmuxIOState[S, A]':
        return self.cons(run_f)

    def inspect(self, f: Callable[[S], A]) -> 'TmuxIOState[S, A]':
        def g(s: S) -> TmuxIO[Tuple[S, A]]:
            return monad.pure((s, f(s)))
        return self.apply(g)

    def inspect_f(self, f: Callable[[S], TmuxIO[A]]) -> 'TmuxIOState[S, A]':
        def g(s: S) -> TmuxIO[Tuple[S, A]]:
            return f(s).map(lambda a: (s, a))
        return self.apply(g)

    def pure(self, a: A) -> 'TmuxIOState[S, A]':
        return self.apply(lambda s: monad.pure((s, a)))

    def reset(self, s: S, a: A) -> 'TmuxIOState[S, A]':
        return self.apply(lambda _: monad.pure((s, a)))

    def reset_t(self, t: Tuple[S, A]) -> 'TmuxIOState[S, A]':
        return self.apply(lambda _: monad.pure(t))

    def delay(self, fa: Callable[..., A], *a: Any, **kw: Any) -> 'TmuxIOState[S, A]':
        return self.apply(lambda s: monad.pure((s, fa(*a, **kw))))

    def lift(self, fa: TmuxIO[A]) -> 'TmuxIOState[S, A]':
        def g(s: S) -> TmuxIO[Tuple[S, A]]:
            return fa.map(lambda a: (s, a))
        return self.apply(g)

    def modify(self, f: Callable[[S], S]) -> 'TmuxIOState[S, None]':
        return self.apply(lambda s: monad.pure((f(s), None)))

    def modify_f(self, f: Callable[[S], TmuxIO[S]]) -> 'TmuxIOState[S, None]':
        return self.apply(lambda s: f(s).map(lambda a: (a, None)))

    def set(self, s: S) -> 'TmuxIOState[S, None]':
        return self.modify(lambda s0: s)

    def get(self) -> 'TmuxIOState[S, S]':
        return self.inspect(lambda a: a)

    @property
    def unit(self) -> 'TmuxIOState[S, None]':
        return TmuxIOState.pure(None)

    def s(self, tpe: Type[S]) -> TmuxIOStateCtor[S]:
        return TmuxIOStateCtor()

    def io(self, f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    def delay(self, f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    def suspend(self, f: Callable[[Tmux], TmuxIO[A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.suspend(f))

    def from_io(self, io: IO[A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.wrap_either(lambda v: io.attempt))

    def from_id(self, st: State[S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.pure(s.value))

    def from_maybe(self, a: Maybe[B], err: CallByName) -> 'TmuxIOState[S, B]':
        return TmuxIOState.lift(TmuxIO.from_maybe(a, err))

    m = from_maybe

    def from_either(self, e: Either[str, A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.from_either(e))

    e = from_either

    def from_either_state(self, st: EitherState[E, S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.from_either(s))

    def failed(self, e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.failed(e))

    def error(self, e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.error(e))

    def inspect_maybe(self, f: Callable[[S], Maybe[A]], err: CallByName) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_maybe(f(s), err))

    def inspect_either(self, f: Callable[[S], Either[str, A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_either(f(s)))

    def simple(self, f: Callable[..., A], *a: Any, **kw: Any) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.simple(f, *a, **kw))

    def sleep(self, duration: float) -> 'TmuxIOState[S, None]':
        return TS.lift(TmuxIO.sleep(duration))

    def modify_e(self, f: Callable[[S], Either[str, S]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_either(f).flat_map(TmuxIOState.set)

    def read(self, cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.read(cmd, *args))

    def write(self, cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.write(cmd, *args))


class TmuxIOState(Generic[S, A], StateT, ToStr, Implicits, implicits=True, auto=True, metaclass=TmuxIOStateMeta):

    def __init__(self, run_f: TmuxIO[Callable[[S], TmuxIO[Tuple[S, A]]]]) -> None:
        self.run_f = run_f

    @property
    def cls(self) -> Type['TmuxIOState[S, A]']:
        return type(self)

    def run(self, s: S) -> TmuxIO[Tuple[S, A]]:
        return self.run_f.flat_map(lambda f: f(s))

    def run_s(self, s: S) -> TmuxIO[S]:
        return self.run(s).map(lambda a: a[0])

    def run_a(self, s: S) -> TmuxIO[S]:
        return self.run(s).map(lambda a: a[1])

    def _arg_desc(self) -> List[str]:
        return List(str(self.run_f))

    def flat_map_f(self, f: Callable[[A], TmuxIO[B]]) -> 'TmuxIOState[S, B]':
        def h(s: S, a: A) -> TmuxIO[Tuple[S, B]]:
            return f(a).map(lambda b: (s, b))
        def g(fsa: TmuxIO[Tuple[S, A]]) -> TmuxIO[Tuple[S, B]]:
            return fsa.flat_map2(h)
        run_f1 = self.run_f.map(lambda sfsa: lambda a: g(sfsa(a)))
        return self.cls.apply_f(run_f1)

    def transform(self, f: Callable[[Tuple[S, A]], Tuple[S, B]]) -> 'TmuxIOState[S, B]':
        def g(fsa: TmuxIO[Tuple[S, A]]) -> TmuxIO[Tuple[S, B]]:
            return fsa.map2(f)
        run_f1 = self.run_f.map(lambda sfsa: lambda a: g(sfsa(a)))
        return self.cls.apply_f(run_f1)

    def transform_s(self, f: Callable[[R], S], g: Callable[[R, S], R]) -> 'TmuxIOState[R, A]':
        def trans(sfsa: Callable[[S], TmuxIO[Tuple[S, A]]], r: R) -> TmuxIO[Tuple[R, A]]:
            s = f(r)
            return sfsa(s).map2(lambda s, a: (g(r, s), a))
        return self.cls.apply_f(self.run_f.map(curried(trans)))

    def transform_f(self, tpe: Type[ST1], f: Callable[[TmuxIO[Tuple[S, A]]], Any]) -> ST1:
        def trans(s: S) -> Any:
            return f(self.run(s))
        return tpe.apply(trans)  # type: ignore

    def zoom(self, l: UnboundLens) -> 'TmuxIOState[R, A]':
        return self.transform_s(l.get(), lambda r, s: l.set(s)(r))

    transform_s_lens = zoom

    def read_zoom(self, l: UnboundLens) -> 'TmuxIOState[R, A]':
        return self.transform_s(l.get(), lambda r, s: r)

    transform_s_lens_read = read_zoom

    def flat_map(self, f: Callable[[A], 'TmuxIOState[S, B]']) -> 'TmuxIOState[S, B]':
        return Monad_TmuxIOState.flat_map(self, f)


def run_function(s: TmuxIOState[S, A]) -> TmuxIO[Callable[[S], TmuxIO[Tuple[S, A]]]]:
    try:
        return s.run_f
    except Exception as e:
        if not isinstance(s, TmuxIOState):
            raise TypeError(f'flatMapped {s} into TmuxIOState')
        else:
            raise


class TmuxIOStateMonad(Monad, tpe=TmuxIOState):

    def pure(self, a: A) -> TmuxIOState[S, A]:  # type: ignore
        return TmuxIOState.pure(a)

    def flat_map(  # type: ignore
            self,
            fa: TmuxIOState[S, A],
            f: Callable[[A], TmuxIOState[S, B]]
    ) -> TmuxIOState[S, B]:
        def h(s: S, a: A) -> TmuxIO[Tuple[S, B]]:
            return f(a).run(s)
        def g(fsa: TmuxIO[Tuple[S, A]]) -> TmuxIO[Tuple[S, B]]:
            return fsa.flat_map2(h)
        def i(sfsa: Callable[[S], TmuxIO[Tuple[S, A]]]) -> Callable[[S], TmuxIO[Tuple[S, B]]]:
            return lambda a: g(sfsa(a))
        run_f1 = run_function(fa).map(i)
        return TmuxIOState.apply_f(run_f1)


Monad_TmuxIOState = TmuxIOStateMonad()


class TmuxIOStateZip(Zip, tpe=TmuxIOState):

    def zip(
            self,
            fa: TmuxIOState[S, A],
            fb: TmuxIOState[S, A],
            *fs: TmuxIOState[S, A],
    ) -> TmuxIOState[S, List[A]]:
        v = ListTraverse().sequence(List(fa, fb, *fs), TmuxIOState)  # type: ignore
        return cast(TmuxIOState[S, List[A]], v)


TS = TmuxIOState


class ToTmuxIOState(TypeClass):

    @abc.abstractproperty
    def tmux(self) -> TS:
        ...


class IdStateToTmuxIOState(ToTmuxIOState, tpe=State):

    @tc_prop
    def tmux(self, fa: State[S, A]) -> TS:
        return TmuxIOState.from_id(fa)


class EitherStateToTmuxIOState(ToTmuxIOState, tpe=EitherState):

    @tc_prop
    def tmux(self, fa: EitherState[E, S, A]) -> TS:
        return TmuxIOState.from_either_state(fa)


class TmuxIOToTmuxIOState(ToTmuxIOState, tpe=TmuxIO):

    @tc_prop
    def tmux(self, fa: TmuxIO[A]) -> TS[S, A]:
        return TS.lift(fa)

    @tc_prop
    def state(self, fa: TmuxIO[A]) -> TS[S, A]:
        return self.tmux(fa)


__all__ = ('TmuxIOState',)
