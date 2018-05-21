from typing import Callable

from kallikrein import k, Expectation

from amino import List, do, Do
from amino.boolean import true
from amino.lenses.lens import lens

from chiasma.commands.pane import all_panes
from chiasma.data.view_tree import map_layouts
from chiasma.ui.simple import has_ident
from chiasma.test.tmux_spec import TmuxSpec
from chiasma.io.state import TS
from chiasma.util.id import StrIdent

from unit._support.data import SpecData, ui_open_pane, open_pane, simple_render
from unit._support.layout import two_vertical, three


def minimize_layout(name: str) -> Callable[[SpecData], SpecData]:
    return lens.layout.modify(
        map_layouts(has_ident(name), lens.state.minimized.set(true))
    )


class MinimizeLayoutSpec(TmuxSpec):
    '''
    minimize a layout with two panes $minimize
    minimize one of two vertical layouts $two_vertical
    '''

    def minimize(self) -> Expectation:
        data = SpecData.cons(three)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_pane(StrIdent('one'))
            yield ui_open_pane(StrIdent('two'))
            yield open_pane(StrIdent('three'))
            yield TS.modify(minimize_layout('sub'))
            yield simple_render()
            yield all_panes().state
        s, panes = self.run(go(), data)
        return k(panes[1:].map(lambda a: a.width)) == List(2, 2)

    def two_vertical(self) -> Expectation:
        data = SpecData.cons(two_vertical)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_pane(StrIdent('one'))
            yield ui_open_pane(StrIdent('two'))
            yield TS.modify(minimize_layout('right'))
            yield simple_render()
            yield all_panes().state
            self._wait(1)
        s, panes = self.run(go(), data)
        return k(panes.drop(1).map(lambda a: a.width)) == List(2)


__all__ = ('MinimizeLayoutSpec',)
