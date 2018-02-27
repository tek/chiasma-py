from typing import TypeVar, Tuple

from amino.dispatch import PatMat
from amino import Maybe, Just, Either, do, Do, __, Nothing

from chiasma.data.view_tree import ViewTree, LayoutNode, PaneNode, SubUiNode
from chiasma.data.tmux import TmuxData
from chiasma.commands.pane import PaneData, window_panes
from chiasma.util.id import Ident
from chiasma.data.pane import Pane
from chiasma.data.session import Session
from chiasma.commands.window import WindowData
from chiasma.pane import add_pane
from chiasma.io.state import TS

L = TypeVar('L')
P = TypeVar('P')


class FindPrincipal(PatMat, alg=ViewTree):

    def layout_node(self, node: LayoutNode[L, P]) -> Maybe[P]:
        return node.sub.find_map(self)

    def pane_node(self, node: PaneNode[L, P]) -> Maybe[P]:
        return Just(node.data)

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Maybe[P]:
        return Nothing


def find_principal(layout: LayoutNode) -> Either[str, P]:
    return FindPrincipal.match(layout).to_either(f'window contains no pane')


@do(TS[TmuxData, PaneData])
def principal_native(window: Ident) -> Do:
    twin = yield TS.inspect_f(__.window_by_ident(window))
    window_id = yield TS.from_either(twin.id.to_either('no window id'))
    panes = yield TS.lift(window_panes(window_id))
    yield TS.from_either(panes.head.to_either(lambda: f'no tmux panes in {window}'))


@do(TS[TmuxData, Tuple[P, Pane]])
def principal(layout: LayoutNode) -> Do:
    pane = yield TS.from_either(find_principal(layout))
    existing = yield TS.inspect(__.pane_by_ident(pane.ident))
    tpane = yield existing / TS.pure | (lambda: add_pane(pane.ident).tmux)
    yield TS.pure((pane, tpane))


@do(TS[TmuxData, None])
def sync_principal(session: Session, window: Ident, layout: LayoutNode, nwindow: WindowData) -> Do:
    (pane, tpane) = yield principal(layout)
    native = yield principal_native(window)
    yield TS.modify(__.update_pane(tpane.copy(id=Just(native.id))))


__all__ = ('find_principal', 'principal_native', 'principal', 'sync_principal')
