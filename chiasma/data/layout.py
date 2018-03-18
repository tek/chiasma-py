from amino import Dat, List, Nil, ADT

from chiasma.util.id import Ident
from chiasma.data.pane import Pane


class View(ADT['View']):
    pass


class Layout(Dat['Layout']):

    @staticmethod
    def cons(
        ident: Ident,
        views: List[View]=Nil,
    ) -> 'Layout':
        return Layout(
            ident,
            views,
        )

    def __init__(self, ident: Ident, views: List[View]) -> None:
        self.ident = ident
        self.views = views

    def add(self, view: View) -> 'Layout':
        return self.append1.views(view)


class PaneView(View):

    def __init__(self, pane: Pane) -> None:
        self.pane = pane


class LayoutView(View):

    def __init__(self, layout: Layout) -> None:
        self.layout = layout


__all__ = ('Layout',)
