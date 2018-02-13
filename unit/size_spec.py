from kallikrein import k, Expectation

from amino.test.spec import SpecBase
from amino import List, Just, Nothing

from chiasma.window.measure import balance_sizes


class SizeSpec(SpecBase):
    '''
    distribute on unbounded $unbounded
    distribute on all $all
    distribute on equally bounded $equal
    cut $cut
    '''

    def unbounded(self) -> Expectation:
        r = balance_sizes(List(0, 0, 5), List(Just(10), Just(10), Nothing), List(1 / 3, 1 / 3, 1 / 3), 50)
        return k(r) == List(10, 10, 30)

    def all(self) -> Expectation:
        r = balance_sizes(List(0, 0, 0), List(Just(10), Just(10), Just(40)), List(0.2, 0.4, 0.4), 50)
        return k(r) == List(10, 10, 30)

    def equal(self) -> Expectation:
        r = balance_sizes(List(0, 0, 0), List(Just(10), Just(10), Just(10)), List(1 / 3, 1 / 3, 1 / 3), 90)
        return k(r) == List(30, 30, 30)

    def cut(self) -> Expectation:
        r = balance_sizes(List(10, 20, 40), List(Nothing, Nothing, Nothing), List(0.2, 0.4, 0.4), 50)
        return k(r) == List(2, 14, 34)


__all__ = ('SizeSpec',)
