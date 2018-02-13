from uuid import uuid4

from amino import Boolean, ADT
from amino.tc.base import tc_prop

from chiasma.util.id import Ident
from chiasma.ui.view_geometry import ViewGeometry
from chiasma.ui.view import UiPane, UiLayout, UiView
from chiasma.ui.state import ViewState


class View(ADT['View']):

    def __init__(self, ident: Ident, state: ViewState, geometry: ViewGeometry) -> None:
        self.ident = ident
        self.state = state
        self.geometry = geometry


class Layout(View):

    @staticmethod
    def cons(
            ident: Ident=None,
            state: ViewState=None,
            geometry: ViewGeometry=None,
            vertical: bool=True,
    ) -> 'Layout':
        return Layout(
            ident or uuid4(),
            state or ViewState.cons(),
            geometry or ViewGeometry.cons(),
            Boolean(vertical),
        )

    def __init__(
            self,
            ident: Ident,
            state: ViewState,
            geometry: ViewGeometry,
            vertical: Boolean,
    ) -> None:
        super().__init__(ident, state, geometry)
        self.vertical = vertical


class Pane(View):

    @staticmethod
    def cons(
            ident: Ident=None,
            state: ViewState=None,
            geometry: ViewGeometry=None,
            open: bool=False,
    ) -> 'Pane':
        return Pane(
            ident or uuid4(),
            state or ViewState.cons(),
            geometry or ViewGeometry.cons(),
            Boolean(open),
        )

    def __init__(
            self,
            ident: Ident,
            state: ViewState,
            geometry: ViewGeometry,
            open: Boolean,
    ) -> None:
        super().__init__(ident, state, geometry)
        self.open = open


class SimpleUiPane(UiPane, tpe=Pane):

    @tc_prop
    def ident(self, a: Pane) -> Ident:
        return a.ident

    @tc_prop
    def open(self, a: Pane) -> Ident:
        return a.open


class SimpleUiLayout(UiLayout, tpe=Layout):
    pass


class SimplePaneUiView(UiView, tpe=Pane):

    def state(self, a: Pane) -> ViewState:
        return a.state

    def geometry(self, a: Pane) -> ViewGeometry:
        return a.geometry


class SimpleLayoutUiView(UiView, tpe=Layout):

    def state(self, a: Layout) -> ViewState:
        return a.state

    def geometry(self, a: Layout) -> ViewGeometry:
        return a.geometry


__all__ = ('View', 'Layout', 'Pane')
