from typing import Tuple

from amino import List, do, Do, Dat, _

from amino.lenses.lens import lens
from amino.boolean import true
from amino.case import Case

from chiasma.data.tmux import Views
from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.ui.simple import SimpleLayout, SimplePane, SimpleViewTree
from chiasma.render import render
from chiasma.io.state import TS
from chiasma.util.id import Ident, StrIdent, IdentSpec
from chiasma.commands.pane import PaneData
from chiasma.open_pane import ui_open_pane


class SpecData(Dat['SpecData']):

    @staticmethod
    def cons(layout: SimpleViewTree=None) -> 'SpecData':
        views = Views.cons(sessions=List(Session.cons('main', id=0)), windows=List(Window.cons('main', id=0)))
        return SpecData(layout or SimpleViewTree.layout(SimpleLayout.cons('root')), views)

    def __init__(self, layout: SimpleViewTree, views: Views) -> None:
        self.layout = layout
        self.views = views


@do(TS[SpecData, None])
def ui_open_simple_pane(spec: IdentSpec) -> Do:
    yield TS.modify_e(ui_open_pane(spec)).zoom(lens.layout)


@do(TS[SpecData, None])
def simple_render() -> Do:
    layout = yield TS.inspect(_.layout)
    yield render(P=SimplePane, L=SimpleLayout)(StrIdent('main'), StrIdent('main'), layout).transform_s_lens(lens.views)


@do(TS[SpecData, None])
def open_simple_pane(ident: Ident) -> Do:
    yield ui_open_simple_pane(ident)
    yield simple_render()
    yield TS.write('display-panes')


def pane_geo(pane: PaneData) -> Tuple[int, int, int]:
    return pane.width, pane.height, pane.position


__all__ = ('SpecData', 'ui_open_pane', 'open_simple_pane', 'pane_geo', 'simple_render',)
