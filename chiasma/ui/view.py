from typing import TypeVar
import abc

from amino.tc.base import TypeClass
from amino import Boolean

from chiasma.util.id import Ident
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
    pass


class UiPane(TypeClass):

    @abc.abstractmethod
    def ident(self, a: A) -> Ident:
        ...

    @abc.abstractmethod
    def open(self, a: A) -> Boolean:
        ...


__all__ = ('UiWindow', 'UiView', 'UiLayout', 'UiPane')
