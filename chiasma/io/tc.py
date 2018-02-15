from typing import TypeVar, Callable

from amino.tc.base import ImplicitInstances
from amino.lazy import lazy
from amino.tc.monad import Monad

from chiasma.io.compute import TmuxIO

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


__all__ = ('TmuxIOInstances',)
