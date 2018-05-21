from kallikrein import k, Expectation
from kallikrein.matchers.length import have_length

from amino.test.spec import SpecBase
from amino import do, Do

from chiasma.io.state import TS
from chiasma.commands.pane import all_panes

from unit._support.data import SpecData, open_simple_pane, ui_open_simple_pane
from unit._support.klk import unit_test, TestConfig
from unit._support.layout import three


test_config = TestConfig.cons(layout=three)


@do(TS[SpecData, Expectation])
def pin_spec() -> Do:
    yield ui_open_simple_pane('one')
    yield open_simple_pane('three')
    s = yield all_panes().state
    return k(s).must(have_length(3))


class PinSpec(SpecBase):
    '''
    open pinned panes when opening a sibling $open_pinned
    '''

    def open_pinned(self) -> Expectation:
        return unit_test(pin_spec, test_config)


__all__ = ('PinSpec',)
