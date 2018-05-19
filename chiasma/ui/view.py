from typing import TypeVar
import abc

from amino.tc.base import TypeClass
from amino import Boolean, Maybe, Path

from chiasma.util.id import Ident, IdentSpec, ensure_ident
from chiasma.ui.state import ViewState
from chiasma.ui.view_geometry import ViewGeometry

A = TypeVar('A')


class UiWindow(TypeClass):

    @abc.abstractmethod
    def name(self, a: A) -> str:
        ...


class UiView(TypeClass):

    @abc.abstractmethod
    def state(self, a: A) -> ViewState:
        ...

    @abc.abstractmethod
    def geometry(self, a: A) -> ViewGeometry:
        ...


class UiLayout(TypeClass):

    @abc.abstractmethod
    def ident(self, a: A) -> Ident:
        ...

    def has_ident(self, a: A, ident: IdentSpec) -> bool:
        return a.ident == ensure_ident(ident)


class UiPane(TypeClass):

    @abc.abstractmethod
    def ident(self, a: A) -> Ident:
        ...

    @abc.abstractmethod
    def open(self, a: A) -> Boolean:
        ...

    @abc.abstractmethod
    def cwd(self, a: A) -> Maybe[Path]:
        ...


__all__ = ('UiWindow', 'UiView', 'UiLayout', 'UiPane')
