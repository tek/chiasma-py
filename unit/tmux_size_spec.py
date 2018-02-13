import pty
import subprocess
from typing import Tuple, TypeVar

from kallikrein import k, Expectation

from amino.test.spec import SpecBase
from amino import List, do, Do, __, Dat, Just, _, Either, Right, Boolean, Left, L, ADT
from amino.state import State
from amino.lenses.lens import lens
from amino.dispatch import PatMat
from amino.boolean import true, false
from amino.test import fixture_path
from amino.tc.context import context, Bindings
from amino.logging import module_log

from chiasma.tmux import Tmux
from chiasma.io.compute import TmuxIO
from chiasma.data.tmux import TmuxData
from chiasma.data.session import Session
from chiasma.data.window import Window as TWindow
from chiasma.data.pane import Pane as TPane
from chiasma.window.measure import measure_view_tree, MeasuredLayoutNode, MeasuredPaneNode
from chiasma.commands.session import session_exists, create_session
from chiasma.commands.window import session_window, create_window, window, WindowData
from chiasma.commands.pane import (pane_from_data, window_panes, pane_open, resize_pane, move_pane,
                                   create_pane_from_data, PaneData, all_panes)
from chiasma.commands.server import kill_server
from chiasma.io.tc import TS
from chiasma.data.view_tree import ViewTree, LayoutNode, PaneNode, layout_panes, map_nodes, find_pane
from chiasma.util.id import Ident
from chiasma.ui.view_geometry import ViewGeometry
from chiasma.ui.simple import Layout, Pane
from chiasma.window.principal import find_principal

log = module_log()
win_width = 300
win_height = 120


def terminal_args() -> list:
    geom = '{}x{}'.format(win_width + 1, win_height + 1)
    return ['urxvt', '-geometry', geom, '-e']


def start_tmux(socket: str, term: bool=False) -> subprocess.Popen:
    conf = fixture_path('conf', 'tmux.conf')
    t = terminal_args() if term else []
    args = t + ['tmux', '-L', socket, '-f', str(conf)]
    master, slave = pty.openpty()
    return subprocess.Popen(args, stdout=slave, stdin=slave, stderr=slave)


A = TypeVar('A')
B = TypeVar('B')
D = TypeVar('D')
P = TypeVar('P')
W = TypeVar('W')


@do(State[TmuxData, Session])
def add_session(ident: Ident) -> Do:
    session = Session.cons(ident)
    yield State.pure(session)


@do(State[TmuxData, Session])
def find_or_create_session(ident: Ident) -> Do:
    existing = yield State.inspect(__.session_by_ident(ident))
    session = existing.cata(lambda err: add_session(ident), State.pure)
    yield session


@do(State[TmuxData, TWindow])
def add_window(ident: Ident) -> Do:
    twindow = TWindow.cons(ident)
    yield State.pure(twindow)


@do(State[TmuxData, TWindow])
def find_or_create_window(ident: Ident) -> Do:
    existing = yield State.inspect(__.window_by_ident(ident))
    yield existing.cata(lambda err: add_window(ident), State.pure)


@do(State[TmuxData, TPane])
def add_pane(ident: Ident) -> Do:
    tpane = TPane.cons(ident)
    yield State.modify(__.add_pane(tpane))
    yield State.pure(tpane)


@do(State[TmuxData, TPane])
def find_or_create_pane(ident: Ident) -> Do:
    existing = yield State.inspect(__.pane_by_ident(ident))
    tpane = existing.cata(lambda err: add_pane(ident), State.pure)
    yield tpane


@do(TmuxIO[None])
def ensure_session(session: Session) -> Do:
    exists = yield session.id.map(session_exists) | TmuxIO.pure(false)
    yield TmuxIO.pure(None) if exists else create_session(session.ident)


@do(TS[TmuxData, WindowData])
def create_tmux_window(session: Session, layout: LayoutNode[A, B], name: str) -> Do:
    princ = yield principal(layout)
    sid = yield TS.from_maybe(session.id, 'no session id')
    window = yield TS.lift(create_window(sid, name))
    yield TS.modify(__.set_principal_id(window, princ))
    yield TS.from_either(window)


@do(TS[TmuxData, TPane])
def add_principal_pane(ident: Ident) -> Do:
    tpane = TPane.cons(ident)
    yield TS.modify(__.append1.panes(tpane))
    yield TS.pure(tpane)


@do(TS[TmuxData, TPane])
def principal_native(window: Ident) -> Do:
    twin = yield TS.inspect_f(__.window_by_ident(window))
    window_id = yield TS.from_either(twin.id.to_either('no window id'))
    panes = yield TS.lift(window_panes(window_id))
    yield TS.from_either(panes.head.to_either(lambda: f'no tmux panes in {window}'))


@do(TS[TmuxData, Tuple[P, TPane]])
def principal(layout: LayoutNode) -> Do:
    pane = yield TS.from_either(find_principal(layout))
    existing = yield TS.inspect(__.pane_by_ident(pane.ident))
    tpane = yield existing / TS.pure | (lambda: add_principal_pane(pane.ident))
    yield TS.pure((pane, tpane))


@do(TS[TmuxData, None])
def sync_principal(session: Session, window: Ident, layout: LayoutNode, nwindow: WindowData) -> Do:
    (pane, tpane) = yield principal(layout)
    native = yield principal_native(window)
    yield TS.modify(__.update_pane(tpane.copy(id=Just(native.id))))


@do(TS[TmuxData, None])
def ensure_window(session: Session, window: TWindow, ui_window: Ident, layout: ViewTree) -> Do:
    @do(Either[str, TmuxIO[Either[str, WindowData]]])
    def existing() -> Do:
        sid = yield session.id.to_either('session has no id')
        wid = yield window.id.to_either('window has no id')
        yield Right(session_window(sid, wid))
    @do(TS[TmuxData, Either[str, WindowData]])
    def sync(win_io: TmuxIO[Either[str, WindowData]]) -> Do:
        win = yield TS.lift(win_io)
        yield (
            win /
            L(sync_principal)(session, ui_window, layout, _) /
            __.map(Right) |
            (lambda: TS.pure(Left('window not open')))
        )
    win = yield (existing() / sync).value
    yield win / TS.pure | (lambda: create_tmux_window(session, window, ui_window))
    yield TS.unit


@do(TS[TmuxData, PaneData])
def create_tmux_pane(window: TWindow, pane: TPane) -> Do:
    data = yield TS.lift(create_pane_from_data(window, pane))
    yield TS.modify(__.set_pane_id(pane, data.id))


@do(TS[TmuxData, PaneData])
def ensure_pane_open(window: TWindow, pane: TPane, npane: Either[str, PaneData]) -> Do:
    yield npane / TS.pure | (lambda: create_tmux_pane(window, pane))


class ensure_view(PatMat, alg=ViewTree):
    '''synchronize a TmuxData window to tmux.
    After this step, all missing tmux entities are considered fatal.
    '''

    def __init__(self, session: Session, window: TWindow) -> None:
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
        yield ensure_pane_open(self.window, tpane, pane1) if pane.open else TS.pure(None)


def pane_id_fatal(pane: TPane) -> TS[D, str]:
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


class position_view(PatMat, alg=ViewTree):

    def __init__(self, vertical: Boolean, reference: Ident) -> None:
        self.vertical = vertical
        self.reference = reference

    @do(TS[TmuxData, None])
    def layout_node(self, node: MeasuredLayoutNode[L, P]) -> Do:
        pane = layout_panes(node).head
        yield pane / _.data.view / L(pack_pane)(_, self.reference, self.vertical) | TS.unit

    @do(TS[TmuxData, None])
    def pane_node(self, node: MeasuredPaneNode) -> Do:
        yield pack_pane(node.data.view, self.reference, self.vertical)
        yield TS.unit


def pane_by_ident(ident: Ident) -> TS[TmuxData, TPane]:
    return TS.inspect_either(__.pane_by_ident(ident))


class resize_view(PatMat, alg=ViewTree):

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


# TODO sort views by `position` attr before positioning
class pack_tree(PatMat, alg=ViewTree):

    def __init__(self, session: Session, window: TWindow, principal: Ident) -> None:
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


class WindowState(ADT['WindowState']):
    pass


class PristineWindow(WindowState):

    def __init__(self, native_window: WindowData, ui_window: Ident, layout: ViewTree, pane: PaneData) -> None:
        self.native_window = native_window
        self.ui_window = ui_window
        self.layout = layout
        self.pane = pane


class TrackedWindow(WindowState):

    def __init__(self, native_window: WindowData, ui_window: Ident, layout: ViewTree, native: PaneData, pane: TPane
                 ) -> None:
        self.native_window = native_window
        self.ui_window = ui_window
        self.layout = layout
        self.native = native
        self.pane = pane


def pane_by_id(id: str) -> TS[TmuxData, Either[str, TPane]]:
    return TS.inspect(__.panes.find(__.id.contains(id)).to_either(lambda: f'no tmux pane for `{id}`'))


@do(TS[TmuxData, WindowState])
def window_state(ui_window: Ident, twindow: TWindow, layout: ViewTree) -> Do:
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
class pack_window(PatMat, alg=WindowState):

    def __init__(self, bindings: Bindings, session: Session, window: TWindow, principal: Ident) -> None:
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
        ref = yield TS.from_either(find_pane(win.pane.pane)(win.layout))
        width, height = int(win.native_window.width), int(win.native_window.height)
        measure_tree = measure_view_tree(self.bindings)(win.layout, width, height)
        yield pack_tree(self.session, self.window, self.principal)(measure_tree, ref)


@context(**pack_window.bounds)
@do(TS[TmuxData, None])
def render(bindings: Bindings, session: Ident, ui_window: Ident, layout: ViewTree[L, P]) -> Do:
    session = yield find_or_create_session(session).tmux
    window = yield find_or_create_window(ui_window).tmux
    yield TS.lift(ensure_session(session))
    yield ensure_window(session, window, ui_window, layout)
    yield ensure_view(session, window)(layout)
    ui_princ, t_princ = yield principal(layout)
    ws = yield window_state(ui_window, window, layout)
    yield pack_window(bindings)(session, window, ui_princ)(ws)


class SpecData(Dat['SpecData']):

    @staticmethod
    def cons(layout: ViewTree) -> 'SpecData':
        tm = TmuxData.cons(sessions=List(Session.cons('main', id=0)), windows=List(TWindow.cons('main', id=0)))
        return SpecData(layout, tm)

    def __init__(self, layout: ViewTree, tmux: TmuxData) -> None:
        self.layout = layout
        self.tmux = tmux


@do(TS[SpecData, None])
def ui_open_pane(name: str) -> Do:
    layout = yield TS.inspect(_.layout)
    updated = yield TS.from_either(map_nodes(lambda a: Boolean(a.data.ident == name), lens.data.open.set(true))(layout))
    yield TS.modify(__.set.layout(updated))


@do(TS[SpecData, None])
def open_pane(name: str) -> Do:
    yield ui_open_pane(name)
    layout = yield TS.inspect(_.layout)
    yield render(P=Pane, L=Layout)('main', 'main', layout).transform_s_lens(lens.tmux)
    yield TS.write('display-panes')


class TmuxSpec(SpecBase):

    def setup(self) -> None:
        self.socket = 'op'
        self.proc = start_tmux(self.socket, True)
        self.tmux = Tmux.cons(self.socket)
        self._wait(1)
        cmd = TmuxIO.read('list-clients -F "#{client_name}"')
        self.client = cmd.unsafe(self.tmux).head.get_or_fail('no clients')

    def teardown(self) -> None:
        self.proc.kill()
        self.proc.wait()
        kill_server().result(self.tmux)

    def run(self, prog: TS[SpecData, None], data: SpecData) -> None:
        self._wait(1)
        r = prog.run(data).unsafe(self.tmux)
        TmuxIO.write('display-panes', '-t', self.client).result(self.tmux)
        self._wait(1)
        return r


class LayoutSpec(TmuxSpec):
    '''
    main layout vertical with one pane, one sublayout horizontal with two panes $one_sub
    main layout vertical, two sublayouts horizontal with two panes $two_sub
    four nested layouts $four
    '''

    def one_sub(self) -> Expectation:
        layout = ViewTree.layout(
            Layout.cons('main', vertical=true),
            List(
                ViewTree.pane(Pane.cons('one')),
                ViewTree.layout(
                    Layout.cons('sub', vertical=false),
                    List(
                        ViewTree.pane(Pane.cons('two')),
                        ViewTree.pane(Pane.cons('three')),
                    )
                ),
            )
        )
        data = SpecData.cons(layout)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_pane('one')
            yield ui_open_pane('two')
            yield open_pane('three')
            yield all_panes().state
        s, panes = self.run(go(), data)
        target = List(PaneData(0, 301, 44, 0), PaneData(2, 150, 45, 45), PaneData(1, 150, 45, 45))
        return k(panes) == target

    def two_sub(self) -> Expectation:
        layout = ViewTree.layout(
            Layout.cons('main', vertical=true),
            List(
                ViewTree.layout(
                    Layout.cons('sub1', vertical=false),
                    List(
                        ViewTree.pane(Pane.cons('one')),
                        ViewTree.pane(Pane.cons('two')),
                    )
                ),
                ViewTree.layout(
                    Layout.cons('sub2', vertical=false),
                    List(
                        ViewTree.pane(Pane.cons('three')),
                        ViewTree.pane(Pane.cons('four')),
                    )
                ),
            )
        )
        data = SpecData.cons(layout)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_pane('one')
            yield ui_open_pane('two')
            yield ui_open_pane('three')
            yield open_pane('four')
            yield all_panes().state
        s, panes = self.run(go(), data)
        target = List(
            PaneData(0, 150, 11, 0),
            PaneData(2, 150, 11, 0),
            PaneData(3, 150, 78, 12),
            PaneData(1, 150, 78, 12),
        )
        return k(panes) == target

    def four(self) -> Expectation:
        layout = ViewTree.layout(
            Layout.cons('root'),
            List(
                ViewTree.pane(Pane.cons('one', geometry=ViewGeometry.cons(min_size=30))),
                ViewTree.layout(
                    Layout.cons('main', vertical=false),
                    List(
                        ViewTree.pane(Pane.cons('two')),
                        ViewTree.layout(
                            Layout.cons('sub1'),
                            List(
                                ViewTree.pane(Pane.cons('three')),
                                ViewTree.layout(
                                    Layout.cons('sub2', vertical=false),
                                    List(
                                        ViewTree.pane(Pane.cons('four')),
                                        ViewTree.pane(Pane.cons('five')),
                                    )
                                )
                            )
                        )
                    )
                ),
            )
        )
        data = SpecData.cons(layout)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_pane('one')
            yield ui_open_pane('two')
            yield ui_open_pane('three')
            yield ui_open_pane('four')
            yield open_pane('five')
            yield all_panes().state
        s, panes = self.run(go(), data)
        target = List(
            PaneData(0, 301, 59, 0),
            PaneData(4, 150, 30, 60),
            PaneData(3, 150, 2, 60),
            PaneData(2, 75, 27, 63),
            PaneData(1, 74, 27, 63),
        )
        return k(panes) == target


class DistributeSizeSpec(TmuxSpec):
    '''three panes $three
    '''

    def three(self) -> Expectation:
        layout = ViewTree.layout(
            Layout.cons('root', vertical=true),
            List(
                ViewTree.pane(Pane.cons('one', geometry=ViewGeometry.cons(max_size=10))),
                ViewTree.pane(Pane.cons('two', geometry=ViewGeometry.cons(max_size=10))),
                ViewTree.pane(Pane.cons('three', geometry=ViewGeometry.cons(max_size=10))),
            )
        )
        data = SpecData.cons(layout)
        @do(TS[SpecData, List[PaneData]])
        def go() -> Do:
            yield ui_open_pane('one')
            yield ui_open_pane('two')
            yield open_pane('three')
            yield all_panes().state
        s, panes = self.run(go(), data)
        return k(panes / _.position) == List(0, 30, 61)


__all__ = ('LayoutSpec', 'DistributeSizeSpec')
