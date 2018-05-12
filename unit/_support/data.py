from typing import Tuple


from amino import List, do, Do, __, Dat, _, Boolean
from amino.lenses.lens import lens
from amino.boolean import true

from chiasma.data.tmux import TmuxData
from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.data.view_tree import ViewTree, map_panes
from chiasma.ui.simple import Layout as SimpleLayout, Pane as SimplePane
from chiasma.render import render
from chiasma.io.state import TS
from chiasma.util.id import Ident, StrIdent, IdentSpec, ensure_ident
from chiasma.commands.pane import PaneData


class SpecData(Dat['SpecData']):

    @staticmethod
    def cons(layout: ViewTree) -> 'SpecData':
        tm = TmuxData.cons(sessions=List(Session.cons('main', id=0)), windows=List(Window.cons('main', id=0)))
        return SpecData(layout, tm)

    def __init__(self, layout: ViewTree, tmux: TmuxData) -> None:
        self.layout = layout
        self.tmux = tmux


@do(TS[SpecData, None])
def ui_open_pane(spec: IdentSpec) -> Do:
    ident = ensure_ident(spec)
    layout = yield TS.inspect(_.layout)
    updated = map_panes(P=SimplePane)(lambda a: Boolean(a.ident == ident), lens.open.set(true))(layout)
    yield TS.modify(__.set.layout(updated))


@do(TS[SpecData, None])
def open_pane(ident: Ident) -> Do:
    yield ui_open_pane(ident)
    layout = yield TS.inspect(_.layout)
    yield render(P=SimplePane, L=SimpleLayout)(StrIdent('main'), StrIdent('main'), layout).transform_s_lens(lens.tmux)
    yield TS.write('display-panes')


def pane_geo(pane: PaneData) -> Tuple[int, int, int]:
    return pane.width, pane.height, pane.position


__all__ = ('SpecData', 'ui_open_pane', 'open_pane', 'pane_geo',)
