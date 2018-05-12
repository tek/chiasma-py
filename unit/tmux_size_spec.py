from kallikrein import k, Expectation

from amino import List, do, Do, _
from amino.boolean import true, false

from chiasma.commands.pane import PaneData, all_panes
from chiasma.data.view_tree import ViewTree
from chiasma.ui.view_geometry import ViewGeometry
from chiasma.ui.simple import Layout as SimpleLayout, Pane as SimplePane
from chiasma.test.tmux_spec import TmuxSpec
from chiasma.io.state import TS
from chiasma.util.id import StrIdent

from unit._support.data import SpecData, ui_open_pane, open_pane, pane_geo


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
            yield ui_open_pane(StrIdent('one'))
            yield ui_open_pane(StrIdent('two'))
            yield open_pane(StrIdent('three'))
            yield all_panes().state
        s, panes = self.run(go(), data)
        target = List((301, 44, 0), (150, 45, 45), (150, 45, 45))
        return k(panes / pane_geo) == target

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
            (150, 5, 0),
            (150, 5, 0),
            (150, 84, 6),
            (150, 84, 6),
        )
        return k(panes / pane_geo) == target

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
            (301, 59, 0),
            (150, 2, 60),
            (150, 2, 60),
            (226, 27, 63),
            (74, 27, 63),
        )
        return k(panes / pane_geo) == target


class DistributeSizeSpec(TmuxSpec):
    '''three panes $three
    '''

    def three(self) -> Expectation:
        layout = ViewTree.layout(
            SimpleLayout.cons('root', vertical=true),
            List(
                ViewTree.pane(SimplePane.cons(StrIdent('one'), geometry=ViewGeometry.cons(max_size=10))),
                ViewTree.pane(SimplePane.cons(StrIdent('two'), geometry=ViewGeometry.cons(max_size=10))),
                ViewTree.pane(SimplePane.cons(StrIdent('three'), geometry=ViewGeometry.cons(max_size=10))),
            )
        )
        data = SpecData.cons(layout)
        @do(TS[SpecData, List[PaneData]])
        def go() -> Do:
            yield ui_open_pane(StrIdent('one'))
            yield ui_open_pane(StrIdent('two'))
            yield open_pane(StrIdent('three'))
            yield all_panes().state
        s, panes = self.run(go(), data)
        return k(panes / _.position) == List(0, 30, 60)


__all__ = ('LayoutSpec', 'DistributeSizeSpec')
