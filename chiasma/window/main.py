from typing import TypeVar

from amino.state import State
from amino import do, Do, __, Either, Right, L, _, Left, Boolean, ADT
from amino.case import Case
from amino.logging import module_log
from amino.tc.context import context, Bindings

from chiasma.data.tmux import TmuxData
from chiasma.data.window import Window
from chiasma.util.id import Ident
from chiasma.commands.window import WindowData, create_window, session_window, window
from chiasma.data.session import Session
from chiasma.data.view_tree import LayoutNode, ViewTree, PaneNode, layout_panes, find_pane, SubUiNode
from chiasma.window.principal import principal, sync_principal
from chiasma.io.compute import TmuxIO
from chiasma.pane import (find_or_create_pane, ensure_pane_open, pack_pane, pane_by_ident, pane_id_fatal,
                          reference_pane, pane_by_id, ensure_pane_closed)
from chiasma.commands.pane import pane_from_data, resize_pane, PaneData, window_panes
from chiasma.window.measure import MeasuredLayoutNode, MeasuredPaneNode, measure_view_tree
from chiasma.data.pane import Pane
from chiasma.io.state import TS

log = module_log()
A = TypeVar('A')
B = TypeVar('B')
P = TypeVar('P')
LO = TypeVar('LO')


@do(State[TmuxData, Window])
def add_window(ident: Ident) -> Do:
    twindow = Window.cons(ident)
    yield State.pure(twindow)


@do(State[TmuxData, Window])
def find_or_create_window(ident: Ident) -> Do:
    existing = yield State.inspect(__.window_by_ident(ident))
    yield existing.cata(lambda err: add_window(ident), State.pure)


@do(TS[TmuxData, WindowData])
def create_tmux_window(session: Session, ident: Ident) -> Do:
    sid = yield TS.from_maybe(session.id, 'no session id')
    yield TS.lift(create_window(sid, ident.str))


@do(TmuxIO[Either[str, WindowData]])
def existing_window(session: Session, window: Window) -> Do:
    sid = yield TmuxIO.from_maybe(session.id, 'session has no id')
    wid = yield TmuxIO.from_maybe(window.id, 'window has no id')
    e = yield session_window(sid, wid)
    yield TmuxIO.from_either(e)


@do(TS[TmuxData, Window])
def ensure_window(session: Session, window: Window, window_ident: Ident, layout: ViewTree) -> Do:
    @do(TS[TmuxData, Window])
    def create(error: str) -> Do:
        log.debug(f'creating missing tmux window {window} ({window_ident}) because {error}')
        yield create_tmux_window(session, window_ident)
    io = existing_window(session, window).map(TS.pure).recover_error(create)
    window_data = yield TS.lift(io).join
    yield sync_principal(window_ident, layout)
    return Window.cons(window_ident, window_data.id)


class ensure_view(Case, alg=ViewTree):
    '''synchronize a TmuxData window to tmux.
    After this step, all missing tmux entities are considered fatal.
    '''

    def __init__(self, session: Session, window: Window) -> None:
        self.session = session
        self.window = window

    @do(TS[TmuxData, None])
    def layout_node(self, layout: LayoutNode) -> Do:
        yield layout.sub.traverse(self, TS)

    @do(TS[TmuxData, None])
    def pane_node(self, node: PaneNode) -> Do:
        pane = node.data
        tpane = yield find_or_create_pane(node.data.ident).tmux
        pane1 = yield TS.lift(pane_from_data(self.window, tpane))
        yield (
            ensure_pane_open(self.window, tpane, pane1)
            if pane.open else
            ensure_pane_closed(self.window, tpane, pane1)
        )

    def sub_ui_node(self, node: SubUiNode[L, P]) -> TS[TmuxData, None]:
        return TS.unit


class position_view(Case, alg=ViewTree):

    def __init__(self, vertical: Boolean, reference: Ident) -> None:
        self.vertical = vertical
        self.reference = reference

    @do(TS[TmuxData, None])
    def layout_node(self, node: MeasuredLayoutNode[LO, P]) -> Do:
        pane = layout_panes(node).head
        yield pane / _.data.view / L(pack_pane)(_, self.reference, self.vertical) | TS.unit

    @do(TS[TmuxData, None])
    def pane_node(self, node: MeasuredPaneNode) -> Do:
        yield pack_pane(node.data.view, self.reference, self.vertical)
        yield TS.unit

    def sub_ui_node(self, node: SubUiNode[L, P]) -> TS[TmuxData, None]:
        return TS.unit


class resize_view(Case, alg=ViewTree):

    def __init__(self, vertical: Boolean, reference: Ident) -> None:
        self.vertical = vertical
        self.reference = reference

    @do(TS[TmuxData, None])
    def layout_node(self, node: MeasuredLayoutNode) -> Do:
        yield TS.unit

    @do(TS[TmuxData, None])
    def pane_node(self, node: MeasuredPaneNode) -> Do:
        mp = node.data
        size = mp.measures.size
        tpane = yield pane_by_ident(mp.view.ident)
        id = yield pane_id_fatal(tpane)
        log.debug(f'resize {mp.view} to {size} ({self.vertical})')
        yield TS.lift(resize_pane(id, self.vertical, size))

    def sub_ui_node(self, node: SubUiNode[L, P]) -> TS[TmuxData, None]:
        return TS.unit


# TODO sort views by `position` attr before positioning
class pack_tree(Case, alg=ViewTree):

    def __init__(self, session: Session, window: Window, principal: Ident) -> None:
        self.session = session
        self.window = window
        self.principal = principal

    @do(TS[TmuxData, None])
    def layout_node(self, node: MeasuredLayoutNode, reference: P) -> Do:
        vertical = node.data.view.vertical
        layout_reference = yield reference_pane(node)
        new_reference = layout_reference | reference
        yield node.sub.traverse(position_view(vertical, new_reference), TS)
        yield node.sub.traverse(L(self)(_, new_reference), TS)
        yield node.sub.traverse(resize_view(vertical, new_reference), TS)
        yield TS.unit

    @do(TS[TmuxData, None])
    def pane_node(self, node: PaneNode, reference: P) -> Do:
        yield TS.unit

    def sub_ui_node(self, node: SubUiNode[L, P], reference: P) -> TS[TmuxData, None]:
        return TS.unit


class WindowState(ADT['WindowState']):
    pass


class PristineWindow(WindowState):

    def __init__(self, native_window: WindowData, ui_window: Ident, layout: ViewTree, pane: PaneData) -> None:
        self.native_window = native_window
        self.ui_window = ui_window
        self.layout = layout
        self.pane = pane


class TrackedWindow(WindowState):

    def __init__(self, native_window: WindowData, ui_window: Ident, layout: ViewTree, native: PaneData, pane: Pane
                 ) -> None:
        self.native_window = native_window
        self.ui_window = ui_window
        self.layout = layout
        self.native = native
        self.pane = pane


@do(TS[TmuxData, WindowState])
def window_state(ui_window: Ident, twindow: Window, layout: ViewTree) -> Do:
    window_id = yield TS.from_maybe(twindow.id, 'window_state: `{twindow}` has no id')
    native_window_e = yield TS.lift(window(window_id))
    native_window = yield TS.from_either(native_window_e)
    panes = yield TS.lift(window_panes(window_id))
    native_pane, tail = yield TS.from_maybe(panes.detach_head, 'no panes in window')
    reference_pane = yield pane_by_id(native_pane.id)
    state = (
        reference_pane
        .map(L(TrackedWindow)(native_window, ui_window, layout, native_pane, _)) |
        L(PristineWindow)(native_window, ui_window, layout, native_pane)
    )
    yield TS.pure(state)


@context(**measure_view_tree.bounds)
class pack_window(Case, alg=WindowState):

    def __init__(self, bindings: Bindings, session: Session, window: Window, principal: Ident) -> None:
        self.bindings = bindings
        self.session = session
        self.window = window
        self.principal = principal

    @do(TS[TmuxData, None])
    def pristine_window(self, win: PristineWindow) -> Do:
        yield TS.unit
        # yield pack_tree(session, window, ui_princ)(ui_window.layout, false, Left('initial'))

    @do(TS[TmuxData, None])
    def tracked_window(self, win: TrackedWindow) -> Do:
        ref = yield TS.from_either(find_pane(win.pane.ident)(win.layout))
        width, height = int(win.native_window.width), int(win.native_window.height)
        measure_tree = measure_view_tree(self.bindings)(win.layout, width, height)
        yield pack_tree(self.session, self.window, self.principal)(measure_tree, ref)


__all__ = ('add_window', 'find_or_create_window', 'create_tmux_window', 'ensure_window', 'ensure_view', 'position_view',
           'resize_view', 'pack_tree', 'WindowState', 'PristineWindow', 'TrackedWindow', 'window_state', 'pack_window')
