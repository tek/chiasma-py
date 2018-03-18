from amino import Dat, List, Nil, ADT

from chiasma.util.id import Ident
from chiasma.data.pane import Pane


class View(ADT['View']):
    pass


class Layout(Dat['Layout']):

    @staticmethod
    def cons(
        ident: Ident,
    ) -> 'Layout':
        return Layout(
            ident,
        )

    def __init__(self, ident: Ident, views: List[View]) -> None:
        self.ident = ident


class PaneView(View):

    def __init__(self, pane: Pane) -> None:
        self.pane = pane


class LayoutView(View):

    def __init__(self, layout: Layout) -> None:
        self.layout = layout


__all__ = ('Layout',)
