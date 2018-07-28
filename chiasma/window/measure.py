from typing import Callable, Generic, TypeVar
import operator

from amino.case import Case
from amino import Either, Dat, _, List, Boolean, Maybe, Nil, Just, __, Left
from amino.logging import module_log
from amino.tc.context import context, Bindings

from chiasma.data.view_tree import ViewTree, LayoutNode, PaneNode, SubUiNode
from chiasma.ui.view import UiPane, UiLayout, UiView
from chiasma.ui.view_geometry import ViewGeometry
from chiasma.ui.state import ViewState

log = module_log()
A = TypeVar('A')
B = TypeVar('B')
P = TypeVar('P')
L = TypeVar('L')
V = TypeVar('V')


class Measures(Dat['Measures']):

    def __init__(self, size: float) -> None:
        self.size = size


class MeasuredView(Generic[A], Dat['MeasuredView[A]']):

    def __init__(self, view: A, measures: Measures) -> None:
        self.view = view
        self.measures = measures


MeasureTree = ViewTree[MeasuredView[A], MeasuredView[B]]
MeasuredLayoutNode = LayoutNode[MeasuredView[A], MeasuredView[B]]
MeasuredPaneNode = PaneNode[MeasuredView[A], MeasuredView[B]]


class ViewMeasureData(Dat['ViewMeasureData']):

    def __init__(self, state: ViewState, geometry: ViewGeometry) -> None:
        self.state = state
        self.geometry = geometry


@context(V=UiView)
def measure_data(v: V) -> ViewMeasureData:
    return ViewMeasureData(v.state, v.geometry)


@context(P=UiPane)
class is_view_open(Case, alg=ViewTree):

    def pane_node(self, node: PaneNode[A, P]) -> Either[str, P]:
        return node.data.open

    def layout_node(self, node: LayoutNode[A, P]) -> Either[str, P]:
        return node.sub.exists(self)

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Either[str, P]:
        return Left('SubUiNode')


@context(P=UiPane)
def open_views(bindings: Bindings, node: LayoutNode[A, P]) -> List[ViewTree[A, P]]:
    return node.sub.filter(is_view_open(bindings)())


def measure_layout_views(views: List[ViewMeasureData], total: float) -> List[float]:
    # each pane spacer takes up one cell
    pane_spacers = views.length - 1
    cells = total - pane_spacers
    in_cells = lambda s: s if s > 1 else s * cells
    min_s = actual_min_sizes(views) / in_cells
    max_s = actual_max_sizes(views) / __.map(in_cells)
    minimized = views.map(lambda a: a.state.minimized)
    return balance_sizes(min_s, max_s, view_weights(views), minimized, cells) / round


@context(P=UiPane, L=UiLayout)
class measure_layout(Case, alg=ViewTree):

    def __init__(self, bindings: Bindings, measures: Measures, width: float, height: float) -> None:
        self.bindings = bindings
        self.measures = measures
        self.width = width
        self.height = height

    def pane_node(self, node: PaneNode[A, P]) -> MeasureTree:
        return ViewTree.pane(MeasuredView(node.data, self.measures))

    def layout_node(self, node: LayoutNode[A, P]) -> MeasureTree:
        vertical = node.data.vertical
        total = self.height if vertical else self.width
        views = open_views(self.bindings)(node)
        def recurse(next_node: ViewTree[A, P], size: float) -> MeasureTree:
            new_width, new_height = (self.width, size) if vertical else (size, self.height)
            next_measures = Measures(size)
            return measure_layout(self.bindings)(next_measures, new_width, new_height)(next_node)
        def measure_views() -> List[MeasureTree]:
            sizes = measure_layout_views(views / _.data / measure_data(V=self.bindings.bindings['P']), total)
            return views.zip(sizes).map2(recurse)
        sub = (
            measure_views()
            if views.length > 0 else
            Nil
        )
        return ViewTree.layout(MeasuredView(node.data, self.measures), sub)

    def sub_ui_node(self, node: SubUiNode[L, P]) -> Either[str, P]:
        return ViewTree.pane(MeasuredView(node.data, self.measures))


@context(P=UiPane, L=UiLayout)
def measure_view_tree(bindings: Bindings, layout: LayoutNode[L, P], width: float, height: float) -> MeasureTree:
    size = height if layout.data.vertical else width
    return measure_layout(bindings)(Measures(size), width, height)(layout)


def positive(a: float) -> float:
    return max(a, 0)


def reverse_weights(weights):
    r = weights / (1 - _)
    norm = sum(r)
    return r / (_ / norm) if norm > 0 else r


def minimized_size(data: ViewMeasureData) -> float:
    return data.geometry.minimized_size | 2


def effective_weight(data: ViewMeasureData) -> Maybe[float]:
    return Just(0) if data.geometry.fixed_size.present or data.state.minimized else data.geometry.weight


def effective_fixed_size(data: ViewMeasureData) -> Maybe[float]:
    return data.state.minimized.cata(Just(minimized_size(data)), data.geometry.fixed_size)


def actual_size(view: ViewMeasureData, attr: Callable[[ViewMeasureData], Maybe[float]]) -> Maybe[float]:
    return effective_fixed_size(view).or_else(attr(view.geometry))


def actual_sizes(views: List[ViewMeasureData], attr: Callable[[ViewMeasureData], Maybe[float]], default: float
                 ) -> List[float]:
    return views / (lambda a: actual_size(a, attr) | default)


def actual_min_sizes(views: List[ViewMeasureData]) -> List[float]:
    return actual_sizes(views, _.min_size, 0)


def actual_max_sizes(views: List[ViewMeasureData]) -> List[Maybe[float]]:
    return views / (lambda a: actual_size(a, _.max_size))


def normalize_weights(weights: List[float]) -> List[float]:
    total = sum(weights) or 1
    return weights.map(_ / total)


def amend_and_normalize_weights(weights: List[Maybe[float]]) -> List[float]:
    return normalize_weights(amend_weights(weights))


def view_weights(views: List[ViewMeasureData]) -> List[float]:
    return amend_and_normalize_weights(views / effective_weight)


class Balance(Dat['Balance']):

    def __init__(
            self,
            min: List[float],
            max: List[Maybe[float]],
            weights: List[float],
            minimized: List[bool],
            total: float,
    ) -> None:
        self.min = min
        self.max = max
        self.weights = weights
        self.minimized = minimized
        self.total = total


def balance_sizes(
        min_s: List[float],
        max_s: List[Maybe[float]],
        weights: List[float],
        minimized: List[bool],
        total: float,
) -> List[int]:
    data = Balance(min_s, max_s, weights, minimized, total)
    fitted = (
        cut_sizes(data)
        if sum(min_s) > total else
        distribute_sizes(data)
    )
    return rectify_sizes(fitted) / int


def rectify_sizes(sizes: List[float]) -> List[float]:
    pos = sizes / positive
    pos_count = sizes.filter(_ >= 2).length
    unders = pos / (lambda a: 2 - a if a < 2 else 0)
    sub = sum(unders) / pos_count
    return pos / (lambda a: 2 if a < 2 else max(2, a - sub))


def cut_sizes(data: Balance) -> List[float]:
    log.debug(f'cut sizes: min {data.min}, weights {data.weights}, total {data.total}')
    surplus = sum(data.min) - data.total
    dist = reverse_weights(data.weights) / (surplus * _)
    cut = (data.min.zip(dist)).map2(operator.sub)
    neg = (cut / (lambda a: a if a < 0 else 0))
    neg_total = sum(neg)
    neg_count = neg.filter(_ < 0).length
    dist2 = neg_total / (data.min.length - neg_count)
    return cut / (lambda a: 0 if a < 0 else a + dist2)


def distribute_on_unbounded(data: Balance) -> List[float]:
    initial = data.max.zip(data.min).map2(lambda a, b: a | b)
    new_weights = normalize_weights(data.max.zip(data.weights).map2(lambda m, w: m.replace(0) | w))
    surplus = data.total - sum(initial)
    return initial.zip(new_weights).map2(lambda i, w: i + w * surplus)


def saturate(initial: List[float], max_s: List[float], initial_weights: List[float], total: float) -> List[float]:
    def loop(current: List[float], weights: List[float]) -> List[float]:
        rest = total - sum(current)
        unsat_weights = current.zip(max_s, weights).map3(lambda s, m, w: 0 if s >= m else w)
        new_weights = normalize_weights(unsat_weights)
        new = current.zip(max_s, new_weights).map3(lambda l, h, w: min(l + w * rest, h))
        return (
            new
            if new == current or rest <= 0
            else loop(new, new_weights)
        )
    return loop(initial, initial_weights)


def weights_without_minimized(data: Balance) -> List[float]:
    return normalize_weights(data.weights.zip(data.minimized).map2(lambda w, m: 0 if m else w))


def trim_weights(data: Balance, unsat: List[Boolean]):
    w1 = (unsat.zip(weights_without_minimized(data))).map2(lambda s, w: s.maybe(w))
    return amend_and_normalize_weights(w1)


def distribute_on_all(data: Balance) -> List[float]:
    max_s = data.max / (_ | 10e6)
    min_surplus = data.total - sum(data.min)
    sizes = data.min.zip(max_s, data.weights).map3(lambda l, h, w: min(l + w * min_surplus, h))
    sizes = saturate(data.min, max_s, data.weights, data.total)
    rest = data.total - sum(sizes)
    def dist_rest() -> List[float]:
        unsat = (max_s.zip(sizes)).map2(operator.gt) / Boolean
        unsat_left = sum(unsat / _.to_int) > 0
        rest_w = trim_weights(data, unsat) if unsat_left else weights_without_minimized(data)
        return (sizes.zip(rest_w)).map2(lambda a, w: a + w * rest)
    return sizes if rest <= 0 else dist_rest()


def has_unbounded(data: Balance) -> bool:
    return data.max.exists(lambda a: not a.present)


def distribute_sizes(data: Balance) -> List[float]:
    log.debug(f'distribute sizes: min {data.min}, max {data.max}, weights {data.weights}, total {data.total}')
    max_total = sum(data.max.join)
    handler = distribute_on_unbounded if max_total < data.total and has_unbounded(data) else distribute_on_all
    return handler(data)


def amend_weights(weights: List[Maybe[float]]) -> List[float]:
    total = sum(weights.join) or 1
    empties = weights.filter(_.is_empty).length or 1
    empty_weight = total / empties
    return weights / (_ | empty_weight)


__all__ = ('measure_layout', 'measure_view_tree')
