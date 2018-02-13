from uuid import uuid4

from amino import Dat, List, Nil, ADT

from chiasma.util.id import Ident
from chiasma.data.pane import Pane


class View(ADT['View']):
    pass


class Layout(Dat['Layout']):

    @staticmethod
    def cons(
        views: List[View]=Nil,
        ident: Ident=None,
    ) -> 'Layout':
        return Layout(
            views,
            ident or uuid4(),
        )

    def __init__(self, views: List[View], ident: Ident) -> None:
        self.views = views
        self.ident = ident

    def add(self, view: View) -> 'Layout':
        return self.append1.views(view)


class PaneView(View):

    def __init__(self, pane: Pane) -> None:
        self.pane = pane


class LayoutView(View):

    def __init__(self, layout: Layout) -> None:
        self.layout = layout


__all__ = ('Layout',)
