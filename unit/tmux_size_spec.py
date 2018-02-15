from typing import TypeVar

from kallikrein import k, Expectation

from amino import List, do, Do, __, Dat, _, Boolean
from amino.lenses.lens import lens
from amino.boolean import true, false

from chiasma.data.tmux import TmuxData
from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.commands.pane import PaneData, all_panes
from chiasma.data.view_tree import ViewTree, map_nodes
from chiasma.ui.view_geometry import ViewGeometry
from chiasma.ui.simple import Layout as SimpleLayout, Pane as SimplePane
from chiasma.render import render
from chiasma.test.tmux_spec import TmuxSpec
from chiasma.io.state import TS

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
