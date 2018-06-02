from typing import TypeVar, Generic
import abc

from amino.tc.base import TypeClass
from amino import Boolean, Maybe, Path

from chiasma.util.id import Ident, IdentSpec, ensure_ident_or_generate
from chiasma.ui.state import ViewState
from chiasma.ui.view_geometry import ViewGeometry

A = TypeVar('A')


class UiWindow(Generic[A], TypeClass):

    @abc.abstractmethod
    def name(self, a: A) -> str:
        ...


class UiView(Generic[A], TypeClass):

    @abc.abstractmethod
    def state(self, a: A) -> ViewState:
        ...

    @abc.abstractmethod
    def geometry(self, a: A) -> ViewGeometry:
        ...

    @abc.abstractmethod
    def ident(self, a: A) -> Ident:
        ...

    def has_ident(self, a: A, ident: IdentSpec) -> bool:
        return self.ident(a) == ensure_ident_or_generate(ident)


class UiLayout(Generic[A], TypeClass):
    pass


class UiPane(Generic[A], TypeClass):

    @abc.abstractmethod
    def ident(self, a: A) -> Ident:
        ...

    @abc.abstractmethod
    def open(self, a: A) -> Boolean:
        ...

    @abc.abstractmethod
    def cwd(self, a: A) -> Maybe[Path]:
        ...

    @abc.abstractmethod
    def pin(self, a: A) -> bool:
        ...

    @abc.abstractmethod
    def set_open(self, a: A, state: Boolean) -> A:
        ...


__all__ = ('UiWindow', 'UiView', 'UiLayout', 'UiPane')
