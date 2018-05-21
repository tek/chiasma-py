from kallikrein import k, Expectation

from amino import List, do, Do, Dat, Either
from amino.boolean import true
from amino.util.numeric import parse_int

from chiasma.commands.pane import all_panes, parse_bool, parse_pane_id
from chiasma.data.view_tree import ViewTree
from chiasma.ui.simple import SimpleLayout, SimplePane
from chiasma.test.tmux_spec import TmuxSpec
from chiasma.io.state import TS
from chiasma.util.id import StrIdent
from chiasma.command import tmux_data_cmd, TmuxCmdData
from chiasma.io.compute import TmuxIO

from unit._support.data import SpecData, ui_open_simple_pane, open_simple_pane


class FData(Dat['FData']):

    @staticmethod
    @do(Either[str, 'FData'])
    def cons(
            pane_id: int,
            pane_active: bool,
    ) -> Do:
        id = yield parse_pane_id(pane_id)
        active = yield parse_bool(pane_active)
        return FData(
            id,
            active,
        )

    def __init__(self, id: int, active: bool) -> None:
        self.id = id
        self.active = active


cmd_data_fdata = TmuxCmdData.from_cons(FData.cons)


def pdata() -> TmuxIO[List[FData]]:
    return tmux_data_cmd('list-panes', List('-a'), cmd_data_fdata)


class PaneSpec(TmuxSpec):
    '''
    test $test
    '''

    def test(self) -> Expectation:
        layout = ViewTree.layout(
            SimpleLayout.cons('main', vertical=true),
            List(
                ViewTree.pane(SimplePane.cons('one')),
                ViewTree.pane(SimplePane.cons('two')),
            ),
        )
        data = SpecData.cons(layout)
        @do(TS[SpecData, None])
        def go() -> Do:
            yield ui_open_simple_pane(StrIdent('one'))
            yield open_simple_pane(StrIdent('two'))
            yield all_panes().state
            yield TS.lift(pdata())
        (s, r) = self.run(go(), data)
        return k(r) == List(FData(0, True), FData(1, False))


__all__ = ('PaneSpec',)
