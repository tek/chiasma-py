from typing import TypeVar

from amino.dispatch import PatMat
from amino import Maybe, Just, Either

from chiasma.data.view_tree import ViewTree, LayoutNode, PaneNode

L = TypeVar('L')
P = TypeVar('P')


class FindPrincipal(PatMat, alg=ViewTree):

    def layout_node(self, node: LayoutNode[L, P]) -> Maybe[P]:
        return node.sub.find_map(self)

    def pane_node(self, node: PaneNode[L, P]) -> Maybe[P]:
        return Just(node.data)


def find_principal(layout: LayoutNode) -> Either[str, P]:
    return FindPrincipal.match(layout).to_either(f'window contains no pane')


__all__ = ('find_principal',)
