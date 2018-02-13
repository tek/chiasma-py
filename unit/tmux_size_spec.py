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
from chiasma.data.window import Window
from chiasma.data.pane import Pane
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
from chiasma.ui.simple import Layout as SimpleLayout, Pane as SimplePane
from chiasma.window.principal import find_principal
from chiasma.render import render

from unit._support.tmux import start_tmux

A = TypeVar('A')
B = TypeVar('B')
D = TypeVar('D')
P = TypeVar('P')
W = TypeVar('W')


class SpecData(Dat['SpecData']):

    @staticmethod
    def cons(layout: ViewTree) -> 'SpecData':
        tm = TmuxData.cons(sessions=List(Session.cons('main', id=0)), windows=List(Window.cons('main', id=0)))
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
    yield render(P=SimplePane, L=SimpleLayout)('main', 'main', layout).transform_s_lens(lens.tmux)
    yield TS.write('display-panes')


class TmuxSpec(SpecBase):

    def __init__(self) -> None:
        self.win_width = 300
        self.win_height = 120

    def setup(self) -> None:
        self.socket = 'op'
        self.proc = start_tmux(self.socket, self.win_width, self.win_height, True)
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
            SimpleLayout.cons('main', vertical=true),
            List(
                ViewTree.pane(SimplePane.cons('one')),
                ViewTree.layout(
                    SimpleLayout.cons('sub', vertical=false),
                    List(
                        ViewTree.pane(SimplePane.cons('two')),
                        ViewTree.pane(SimplePane.cons('three')),
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
            SimpleLayout.cons('main', vertical=true),
            List(
                ViewTree.layout(
                    SimpleLayout.cons('sub1', vertical=false),
                    List(
                        ViewTree.pane(SimplePane.cons('one')),
                        ViewTree.pane(SimplePane.cons('two')),
                    )
                ),
                ViewTree.layout(
                    SimpleLayout.cons('sub2', vertical=false),
                    List(
                        ViewTree.pane(SimplePane.cons('three')),
                        ViewTree.pane(SimplePane.cons('four')),
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
            SimpleLayout.cons('root'),
            List(
                ViewTree.pane(SimplePane.cons('one', geometry=ViewGeometry.cons(min_size=30))),
                ViewTree.layout(
                    SimpleLayout.cons('main', vertical=false),
                    List(
                        ViewTree.pane(SimplePane.cons('two')),
                        ViewTree.layout(
                            SimpleLayout.cons('sub1'),
                            List(
                                ViewTree.pane(SimplePane.cons('three')),
                                ViewTree.layout(
                                    SimpleLayout.cons('sub2', vertical=false),
                                    List(
                                        ViewTree.pane(SimplePane.cons('four')),
                                        ViewTree.pane(SimplePane.cons('five')),
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
            SimpleLayout.cons('root', vertical=true),
            List(
                ViewTree.pane(SimplePane.cons('one', geometry=ViewGeometry.cons(max_size=10))),
                ViewTree.pane(SimplePane.cons('two', geometry=ViewGeometry.cons(max_size=10))),
                ViewTree.pane(SimplePane.cons('three', geometry=ViewGeometry.cons(max_size=10))),
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
