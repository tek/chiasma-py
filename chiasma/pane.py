from typing import TypeVar

from amino import do, Do, __, Either, Boolean, _
from amino.state import State
from amino.boolean import false

from chiasma.data.tmux import TmuxData
from chiasma.data.pane import Pane
from chiasma.util.id import Ident
from chiasma.commands.pane import PaneData, create_pane_from_data, pane_open, move_pane, close_pane
from chiasma.data.window import Window
from chiasma.io.compute import TmuxIO
from chiasma.window.measure import MeasuredLayoutNode
from chiasma.data.view_tree import layout_panes
from chiasma.io.state import TS

D = TypeVar('D')
P = TypeVar('P')


@do(State[TmuxData, Pane])
def add_pane(ident: Ident) -> Do:
    tpane = Pane.cons(ident)
    yield State.modify(__.add_pane(tpane))
    yield State.pure(tpane)


@do(State[TmuxData, Pane])
def find_or_create_pane(ident: Ident) -> Do:
    existing = yield State.inspect(__.pane_by_ident(ident))
    tpane = existing.cata(lambda err: add_pane(ident), State.pure)
    yield tpane


@do(TS[TmuxData, PaneData])
def create_tmux_pane(window: Window, pane: Pane) -> Do:
    data = yield TS.lift(create_pane_from_data(window, pane))
    yield TS.modify(__.set_pane_id(pane, data.id))


@do(TS[TmuxData, PaneData])
def ensure_pane_open(window: Window, pane: Pane, npane: Either[str, PaneData]) -> Do:
    yield npane / TS.pure | (lambda: create_tmux_pane(window, pane))


@do(TS[TmuxData, PaneData])
def ensure_pane_closed(window: Window, pane: Pane, npane: Either[str, PaneData]) -> Do:
    yield npane / close_pane / TS.lift | TS.unit


def pane_id_fatal(pane: Pane) -> TS[D, str]:
    return TS.from_either(pane.id.to_either(lambda: f'pane has no id: {pane}'))


@do(TS[TmuxData, Boolean])
def tmux_pane_open(pane: Ident) -> Do:
    tpane = yield pane_by_ident(pane)
    yield TS.lift(tpane.id.cata(pane_open, lambda: TmuxIO.pure(false)))


@do(TS[TmuxData, Either[str, P]])
def reference_pane(node: MeasuredLayoutNode) -> Do:
    open = yield layout_panes(node).map(_.data.view).traverse(lambda p: tmux_pane_open(p.ident).map(__.m(p)), TS)
    yield TS.pure(open.join.head.to_either(f'no open pane in layout'))


@do(TS[TmuxData, None])
def move_tmux_pane(pane: Ident, reference: Ident, vertical: Boolean) -> Do:
    tpane = yield pane_by_ident(pane)
    ref_tpane = yield pane_by_ident(reference)
    id = yield pane_id_fatal(tpane)
    ref_id = yield pane_id_fatal(ref_tpane)
    is_open = yield TS.lift(pane_open(id))
    yield TS.lift(move_pane(id, ref_id, vertical)) if is_open else TS.pure(None)


@do(TS[TmuxData, None])
def pack_pane(pane: P, reference: P, vertical: Boolean) -> Do:
    if pane.open and pane != reference:
        yield move_tmux_pane(pane.ident, reference.ident, vertical)
    yield TS.unit


def pane_by_ident(ident: Ident) -> TS[TmuxData, Pane]:
    return TS.inspect_either(__.pane_by_ident(ident))


def pane_by_id(id: str) -> TS[TmuxData, Either[str, Pane]]:
    return TS.inspect(__.panes.find(__.id.contains(id)).to_either(lambda: f'no tmux pane for `{id}`'))


__all__ = ('add_pane', 'find_or_create_pane', 'create_tmux_pane', 'ensure_pane_open', 'pane_id_fatal', 'tmux_pane_open',
           'reference_pane', 'ensure_pane_open', 'pane_id_fatal', 'tmux_pane_open', 'reference_pane', 'move_tmux_pane',
           'pack_pane', 'pane_by_ident', 'pane_by_id')
