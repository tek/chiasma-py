from typing import Generic, TypeVar, Callable

from amino import ADT, List, Nil, Either, Right, Left, Boolean, _
from amino.dispatch import PatMat
from amino.lenses.lens import lens


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


class reference_node(PatMat, alg=ViewTree):

    def pane_node(self, node: PaneNode[L, P]) -> Either[str, P]:
        return Right(node.data) if node.data.open else Left('pane closed')

    def layout_node(self, node: LayoutNode[L, P]) -> Either[str, L]:
        return node.sub.find_map_e(self).lmap(lambda a: 'no open pane in layout')


class find_pane(PatMat, alg=ViewTree):

    def __init__(self, ident: str) -> None:
        self.ident = ident

    def pane_node(self, node: PaneNode[A, P]) -> Either[str, P]:
        return Right(node.data) if node.data.ident == self.ident else Left(f'pane ident does not match')

    def layout_node(self, node: LayoutNode[A, P]) -> Either[str, P]:
        return node.sub.find_map_e(self, lambda: f'no pane `{self.ident}` in {node}')


def layout_panes(node: LayoutNode) -> List[PaneNode]:
    return node.sub.filter(Boolean.is_a(PaneNode))


class map_nodes(PatMat, alg=ViewTree):

    def __init__(self, pred: Callable, update: Callable) -> None:
        self.pred = pred
        self.update = update

    def layout_node(self, node: LayoutNode) -> Either[str, ViewTree]:
        def update(new: ViewTree) -> ViewTree:
            return lens.sub.Each().Filter(_.data.ident == new.data.ident).set(new)(node)
        return node.sub.find_map(self) / update

    def pane_node(self, node: PaneNode) -> Either[str, ViewTree]:
        return self.pred(node).e(lambda: 'no match', lambda: self.update(node))


__all__ = ('ViewTree', 'PaneNode', 'LayoutNode', 'reference_node', 'find_pane', 'layout_panes', 'map_nodes')
