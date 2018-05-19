from kallikrein import k, Expectation
from kallikrein.matchers.length import have_length

from amino import List, do, Do
from amino.boolean import true, false
from amino.lenses.lens import lens

from chiasma.commands.pane import all_panes
from chiasma.data.view_tree import ViewTree, map_layouts
from chiasma.ui.simple import Layout as SimpleLayout, Pane as SimplePane, SimpleUiLayout
from chiasma.test.tmux_spec import TmuxSpec
from chiasma.io.state import TS
from chiasma.util.id import StrIdent

from unit._support.data import SpecData, ui_open_pane, open_pane, simple_render

layout = ViewTree.layout(
    SimpleLayout.cons('main', vertical=false),
    List(
        ViewTree.pane(SimplePane.cons('one')),
        ViewTree.layout(
            SimpleLayout.cons('sub', vertical=true),
            List(
                ViewTree.pane(SimplePane.cons('two')),
                ViewTree.pane(SimplePane.cons('three')),
            )
        ),
    )
)


def minimize_layout_sub(data: SpecData) -> SpecData:
    return lens.layout.modify(
        map_layouts(lambda a: SimpleUiLayout().has_ident(a, 'sub'), lens.state.minimized.set(true))
    )(data)


class MinimizeLayoutSpec(TmuxSpec):
    '''
    minimize a layout with two panes $minimize
    '''

    def minimize(self) -> Expectation:
        data = SpecData.cons(layout)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_pane(StrIdent('one'))
            yield ui_open_pane(StrIdent('two'))
            yield open_pane(StrIdent('three'))
            yield TS.modify(minimize_layout_sub)
            yield simple_render()
            yield all_panes().state
        s, panes = self.run(go(), data)
        return k(panes[1:].map(lambda a: a.width)) == List(2, 2)


__all__ = ('MinimizeLayoutSpec',)
