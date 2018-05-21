from typing import Tuple, Callable

from amino import List, do, Do, Dat, _, Either, Right, Left, Boolean

from amino.lenses.lens import lens
from amino.boolean import true
from amino.case import Case

from chiasma.data.tmux import Views
from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.ui.simple import SimpleLayout, SimplePane, SimpleViewTree, SimplePaneNode, SimpleLayoutNode
from chiasma.render import render
from chiasma.io.state import TS
from chiasma.util.id import Ident, StrIdent, IdentSpec
from chiasma.commands.pane import PaneData
from chiasma.open_pane import mod_pane, match_ident, ModPaneResult, FoundHere
from chiasma.data.view_tree import SubUiNode, ViewTree


class SpecData(Dat['SpecData']):

    @staticmethod
    def cons(layout: SimpleViewTree=None) -> 'SpecData':
        views = Views.cons(sessions=List(Session.cons('main', id=0)), windows=List(Window.cons('main', id=0)))
        return SpecData(layout or SimpleViewTree.layout(SimpleLayout.cons('root')), views)

    def __init__(self, layout: SimpleViewTree, views: Views) -> None:
        self.layout = layout
        self.views = views


class open_pinned_pane(Case[SimpleViewTree, SimpleViewTree], alg=ViewTree):

    def layout(self, a: SimpleLayoutNode) -> SimpleViewTree:
        return a

    def pane(self, a: SimplePaneNode) -> SimpleViewTree:
        return lens.data.open.set(true)(a)

    def sub_ui(self, a: SubUiNode) -> SimpleViewTree:
        return a


def open_pinned_panes(
        nodes: List[SimpleViewTree],
        results: List[ModPaneResult[SimpleLayout, SimplePane]],
) -> List[SimpleViewTree]:
    found = results.exists(Boolean.is_a(FoundHere))
    return nodes.map(open_pinned_pane.match) if found else nodes


def pane_open_layout_hook(
        layout: SimpleLayoutNode,
        results: List[ModPaneResult[SimpleLayout, SimplePane]],
) -> Either[str, SimpleLayoutNode]:
    return Right(layout.mod.sub(lambda a: open_pinned_panes(a, results)))


def mod_pane_open(spec: IdentSpec) -> Callable[[SimplePaneNode], Either[str, SimplePaneNode]]:
    matches = match_ident(spec)
    def mod_pane_open(node: SimplePaneNode) -> Either[str, SimplePaneNode]:
        return (
            Right(lens.data.open.set(true)(node))
            if matches(node) else
            Left(f'pane ident does not match `{spec}`')
    )
    return mod_pane_open


@do(TS[SpecData, None])
def ui_open_pane(spec: IdentSpec) -> Do:
    yield TS.modify_e(mod_pane(mod_pane_open(spec), pane_open_layout_hook)).zoom(lens.layout)


@do(TS[SpecData, None])
def simple_render() -> Do:
    layout = yield TS.inspect(_.layout)
    yield render(P=SimplePane, L=SimpleLayout)(StrIdent('main'), StrIdent('main'), layout).transform_s_lens(lens.views)


@do(TS[SpecData, None])
def open_pane(ident: Ident) -> Do:
    yield ui_open_pane(ident)
    yield simple_render()
    yield TS.write('display-panes')


def pane_geo(pane: PaneData) -> Tuple[int, int, int]:
    return pane.width, pane.height, pane.position


__all__ = ('SpecData', 'ui_open_pane', 'open_pane', 'pane_geo', 'simple_render',)
