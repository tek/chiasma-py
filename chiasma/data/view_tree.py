from typing import Generic, TypeVar, Callable, Any

from amino import ADT, List, Nil, Either, Right, Left, Boolean, Maybe, Nothing, __, _

from chiasma.ui.view import UiPane
from amino.dispatch import PatMat
from amino.tc.context import context


A = TypeVar('A')
B = TypeVar('B')
L = TypeVar('L')
P = TypeVar('P')


class ViewTree(Generic[A, B], ADT['ViewTree[A, B]']):

    @staticmethod
    def layout(
            data: A,
            sub: List['ViewTree[A, B]']=Nil,
    ) -> 'ViewTree[A, B]':
        return LayoutNode(data, sub)

    @staticmethod
    def pane(data: B) -> 'ViewTree[A, B]':
        return PaneNode(data)


class PaneNode(Generic[A, B], ViewTree[A, B]):

    def __init__(self, data: B) -> None:
        self.data = data


class LayoutNode(Generic[A, B], ViewTree[A, B]):

    def __init__(self, data: A, sub: List[ViewTree[A, B]]) -> None:
        self.data = data
        self.sub = sub

        def replace_sub(node: ViewTree[A, B]) -> LayoutNode[A, B]:
            return self.mod.sub(__.replace_where(node, _.data == node.data))


class SubUiNode(Generic[A, B], ViewTree[A, B]):

    def __init__(self, data: Any) -> None:
        self.data = data


class reference_node(PatMat, alg=ViewTree):

    def pane_node(self, node: PaneNode[L, P]) -> Either[str, P]:
        return Right(node.data) if node.data.open else Left('pane closed')

    def layout_node(self, node: LayoutNode[L, P]) -> Either[str, L]:
        return node.sub.find_map_e(self).lmap(lambda a: 'no open pane in layout')

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Either[str, None]:
        return Left('SubUiNode')


class find_in_view_tree(Generic[L, P], PatMat, alg=ViewTree):

    def __init__(
            self,
            pane: Callable[[PaneNode[L, P]], Maybe[A]]=lambda a: Nothing,
            layout: Callable[[PaneNode[L, P]], Maybe[A]]=lambda a: Nothing,
            sub_ui: Callable[[SubUiNode[L, P]], Maybe[A]]=lambda a: Nothing,
    ) -> None:
        self.pane = pane
        self.layout = layout

    def layout_node(self, node: LayoutNode[L, P]) -> Maybe[A]:
        return self.layout(node).or_else(node.sub.find_map(self))

    def pane_node(self, node: PaneNode[L, P]) -> Maybe[A]:
        return self.pane(node)

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Maybe[A]:
        return self.sub_ui(node)


class find_pane(PatMat, alg=ViewTree):

    def __init__(self, ident: str) -> None:
        self.ident = ident

    def pane_node(self, node: PaneNode[A, P]) -> Either[str, P]:
        return Right(node.data) if node.data.ident == self.ident else Left(f'pane ident does not match')

    def layout_node(self, node: LayoutNode[A, P]) -> Either[str, P]:
        return node.sub.find_map_e(self, lambda: f'no pane `{self.ident}` in {node}')

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Either[str, None]:
        return Left('SubUiNode')


def layout_panes(node: LayoutNode) -> List[PaneNode]:
    return node.sub.filter(Boolean.is_a(PaneNode))


@context(P=UiPane)
class map_panes(PatMat, alg=ViewTree):

    def __init__(self, pred: Callable[[P], bool], update: Callable[[P], P]) -> None:
        self.pred = pred
        self.update = update

    def layout_node(self, node: LayoutNode[L, P]) -> ViewTree:
        return node.mod.sub(__.map(self))

    def pane_node(self, node: PaneNode[L, P]) -> ViewTree:
        return (
            node.mod.data(self.update)
            if self.pred(node.data) else
            node
        )

    def sub_ui_node(self, node: SubUiNode[L, P]) -> ViewTree:
        return node


__all__ = ('ViewTree', 'PaneNode', 'LayoutNode', 'reference_node', 'find_pane', 'layout_panes', 'map_panes',
           'find_in_view_tree')
