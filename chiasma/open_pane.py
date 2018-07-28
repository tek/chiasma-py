from typing import Callable, TypeVar

from amino import List, Either, Right, Left

from amino.lenses.lens import lens
from amino.boolean import true
from amino.case import Case

from chiasma.util.id import IdentSpec
from chiasma.mod_pane import mod_pane, match_ident, ModPaneResult, FoundHere
from chiasma.data.view_tree import SubUiNode, ViewTree, LayoutNode, PaneNode
from chiasma.ui.view import UiPane

L = TypeVar('L')
P = TypeVar('P')


class open_pinned_pane(Case[ViewTree[L, P], ViewTree[L, P]], alg=ViewTree):

    def layout(self, a: LayoutNode[L, P]) -> ViewTree[L, P]:
        return a

    def pane(self, a: PaneNode[L, P]) -> ViewTree[L, P]:
        return (
            lens.data.modify(lambda p: UiPane.fatal_for(p).set_open(p, true))(a)
            if a.data.pin else
            a
        )

    def sub_ui(self, a: SubUiNode) -> ViewTree[L, P]:
        return a


def open_pinned_panes(
        nodes: List[ViewTree[L, P]],
        results: List[ModPaneResult[L, P]],
) -> List[ViewTree[L, P]]:
    found = results.exists(lambda a: isinstance(a, FoundHere) and a.pane.data.open)
    return nodes.map(open_pinned_pane.match) if found else nodes


def pane_open_layout_hook(
        layout: LayoutNode[L, P],
        results: List[ModPaneResult[L, P]],
) -> Either[str, LayoutNode[L, P]]:
    return Right(layout.mod.sub(lambda a: open_pinned_panes(a, results)))


def mod_pane_open(
        spec: IdentSpec,
        mod: Callable[[PaneNode[L, P]], PaneNode[L, P]],
) -> Callable[[PaneNode[L, P]], Either[str, PaneNode[L, P]]]:
    matches = match_ident(spec)
    def mod_pane_open(node: PaneNode[L, P]) -> Either[str, PaneNode[L, P]]:
        return (
            Right(mod(node))
            if matches(node) else
            Left(f'pane ident does not match `{spec}`')
    )
    return mod_pane_open


pane_node_open = lens.data.open


def ui_open_pane(spec: IdentSpec) -> Callable[[ViewTree[L, P]], Either[str, ViewTree[L, P]]]:
    return mod_pane(mod_pane_open(spec, pane_node_open.set(true)), pane_open_layout_hook)


__all__ = ('ui_open_pane', 'ui_toggle_pane',)
