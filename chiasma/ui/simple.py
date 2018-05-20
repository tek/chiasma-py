from typing import Callable

from amino import Boolean, ADT, Maybe, Path
from amino.tc.base import tc_prop

from chiasma.util.id import Ident, IdentSpec, ensure_ident
from chiasma.ui.view_geometry import ViewGeometry
from chiasma.ui.view import UiPane, UiLayout, UiView
from chiasma.ui.state import ViewState
from chiasma.data.view_tree import ViewTree


class SimpleView(ADT['SimpleView']):

    def __init__(self, ident: Ident, state: ViewState, geometry: ViewGeometry) -> None:
        self.ident = ident
        self.state = state
        self.geometry = geometry


class SimpleLayout(SimpleView):

    @staticmethod
    def cons(
            ident: IdentSpec=None,
            state: ViewState=None,
            geometry: ViewGeometry=None,
            vertical: bool=True,
    ) -> 'SimpleLayout':
        return SimpleLayout(
            ensure_ident(ident),
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


class SimplePane(SimpleView):

    @staticmethod
    def cons(
            ident: IdentSpec=None,
            state: ViewState=None,
            geometry: ViewGeometry=None,
            open: bool=False,
            cwd: Path=None,
    ) -> 'SimplePane':
        return SimplePane(
            ensure_ident(ident),
            state or ViewState.cons(),
            geometry or ViewGeometry.cons(),
            Boolean(open),
            Maybe.optional(cwd),
        )

    def __init__(
            self,
            ident: Ident,
            state: ViewState,
            geometry: ViewGeometry,
            open: Boolean,
            cwd: Maybe[Path],
    ) -> None:
        super().__init__(ident, state, geometry)
        self.open = open
        self.cwd = cwd


class SimpleUiPane(UiPane[SimplePane], tpe=SimplePane):

    @tc_prop
    def ident(self, a: SimplePane) -> Ident:
        return a.ident

    @tc_prop
    def open(self, a: SimplePane) -> Boolean:
        return a.open

    def cwd(self, a: SimplePane) -> Maybe[Path]:
        return a.cwd


class SimpleUiLayout(UiLayout[SimpleLayout], tpe=SimpleLayout):

    @tc_prop
    def ident(self, a: SimpleLayout) -> Ident:
        return a.ident


class SimplePaneUiView(UiView[SimplePane], tpe=SimplePane):

    def ident(self, a: SimplePane) -> Ident:
        return a.ident

    def state(self, a: SimplePane) -> ViewState:
        return a.state

    def geometry(self, a: SimplePane) -> ViewGeometry:
        return a.geometry


class SimpleLayoutUiView(UiView[SimpleLayout], tpe=SimpleLayout):

    def ident(self, a: SimpleLayout) -> Ident:
        return a.ident

    def state(self, a: SimpleLayout) -> ViewState:
        return a.state

    def geometry(self, a: SimpleLayout) -> ViewGeometry:
        return a.geometry


def has_ident(ident_spec: IdentSpec) -> Callable[[SimpleView], bool]:
    ident = ensure_ident(ident_spec)
    def has_ident(view: SimpleView) -> bool:
        return view.ident == ident
    return has_ident


SimpleViewTree = ViewTree[SimpleLayout, SimplePane]

__all__ = ('SimpleView', 'SimpleLayout', 'SimplePane', 'has_ident', 'SimpleViewTree',)
