from typing import Generic, TypeVar, Callable, Any

from amino import ADT, List, Nil, Either, Right, Left, Boolean, Maybe, Nothing, __, _, do, Do, Dat

from chiasma.util.id import Ident
from amino.case import Case


A = TypeVar('A')
B = TypeVar('B')
L = TypeVar('L')
P = TypeVar('P')


class ViewTree(Generic[A, B], ADT['ViewTree[A, B]']):

    @staticmethod
    def layout(
            data: A,
            sub: List['ViewTree[A, B]']=Nil,
    ) -> 'LayoutNode[A, B]':
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

    def replace_sub(self, node: ViewTree[A, B]) -> 'LayoutNode[A, B]':
        return self.mod.sub(__.replace_where(node, _.data == node.data))


class SubUiNode(Generic[A, B], ViewTree[A, B]):

    def __init__(self, data: Any) -> None:
        self.data = data


class reference_node(Case, alg=ViewTree):

    def pane_node(self, node: PaneNode[L, P]) -> Either[str, P]:
        return Right(node.data) if node.data.open else Left('pane closed')

    def layout_node(self, node: LayoutNode[L, P]) -> Either[str, L]:
        return node.sub.find_map_e(self).lmap(lambda a: 'no open pane in layout')

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Either[str, None]:
        return Left('SubUiNode')


class find_in_view_tree(Generic[A, L, P], Case[ViewTree[L, P], Maybe[A]], alg=ViewTree):

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


class find_pane(Case, alg=ViewTree):

    def __init__(self, ident: Ident) -> None:
        self.ident = ident

    def pane_node(self, node: PaneNode[A, P]) -> Either[str, P]:
        return Right(node.data) if node.data.ident == self.ident else Left(f'pane ident does not match')

    def layout_node(self, node: LayoutNode[A, P]) -> Either[str, P]:
        return node.sub.find_map_e(self, lambda: f'no pane `{self.ident}` in {node}')

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Either[str, None]:
        return Left('SubUiNode')


def layout_panes(node: LayoutNode) -> List[PaneNode]:
    return node.sub.filter(Boolean.is_a(PaneNode))


class ViewTreeCallbacks(Generic[L, P], Dat['ViewTreeCallbacks[L, P]']):

    @staticmethod
    def cons(
            pred_layout: Callable[[L], bool]=None,
            update_layout: Callable[[L], L]=None,
            pred_pane: Callable[[P], bool]=None,
            update_pane: Callable[[P], P]=None,
    ) -> 'ViewTreeCallbacks':
        return ViewTreeCallbacks(
            pred_layout or (lambda a: False),
            update_layout or (lambda a: a),
            pred_pane or (lambda a: False),
            update_pane or (lambda a: a),
        )

    def __init__(
            self,
            pred_layout: Callable[[L], bool],
            update_layout: Callable[[L], L],
            pred_pane: Callable[[P], bool],
            update_pane: Callable[[P], P],
    ) -> None:
        self.pred_layout = pred_layout
        self.update_layout = update_layout
        self.pred_pane = pred_pane
        self.update_pane = update_pane


class map_view_tree(Case[ViewTree[L, P], ViewTree[L, P]], alg=ViewTree):

    def __init__(self, f: ViewTreeCallbacks[LayoutNode[L, P], PaneNode[L, P]]) -> None:
        self.f = f

    def layout_node(self, node: LayoutNode[L, P]) -> ViewTree:
        sub = node.mod.sub(__.map(self))
        return (
            self.f.update_layout(sub)
            if self.f.pred_layout(sub) else
            sub
        )

    def pane_node(self, node: PaneNode[L, P]) -> ViewTree:
        return (
            self.f.update_pane(node)
            if self.f.pred_pane(node) else
            node
        )

    def sub_ui_node(self, node: SubUiNode[L, P]) -> ViewTree:
        return node


def map_layout_nodes(
        pred: Callable[[LayoutNode[L, P]], bool],
        update: Callable[[LayoutNode[L, P]], LayoutNode[L, P]],
) -> Callable[[ViewTree[L, P]], ViewTree[L, P]]:
    return map_view_tree(ViewTreeCallbacks.cons(pred_layout=pred, update_layout=update))


def map_pane_nodes(
        pred: Callable[[PaneNode[L, P]], bool],
        update: Callable[[PaneNode[L, P]], PaneNode[L, P]],
) -> Callable[[ViewTree[L, P]], ViewTree[L, P]]:
    return map_views(ViewTreeCallbacks.cons(pred_pane=pred, update_pane=update))


def map_views(f: ViewTreeCallbacks[L, P]) -> Callable[[ViewTree], ViewTree]:
    return map_view_tree(ViewTreeCallbacks(
        pred_layout=lambda a: f.pred_layout(a.data),
        update_layout=lambda a: a.mod.data(f.update_layout),
        pred_pane=lambda a: f.pred_pane(a.data),
        update_pane=lambda a: a.mod.data(f.update_pane),
    ))


def map_layouts(
        pred: Callable[[L], bool],
        update: Callable[[L], L],
) -> Callable[[ViewTree[L, P]], ViewTree[L, P]]:
    return map_views(ViewTreeCallbacks.cons(pred_layout=pred, update_layout=update))


def map_panes(
        pred: Callable[[P], bool],
        update: Callable[[P], P],
) -> Callable[[ViewTree[L, P]], ViewTree[L, P]]:
    return map_views(ViewTreeCallbacks.cons(pred_pane=pred, update_pane=update))


__all__ = ('ViewTree', 'PaneNode', 'LayoutNode', 'reference_node', 'find_pane', 'layout_panes', 'map_views',
           'find_in_view_tree', 'map_panes', 'map_layouts', 'map_view_tree', 'map_layout_nodes', 'map_pane_nodes',)
