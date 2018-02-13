from typing import TypeVar, Generic

from amino import Dat, List

from chiasma.data.layout import Layout
from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.ui.data.tree import ViewTree

A = TypeVar('A')


class ViewPath(Generic[A], Dat['ViewPath']):

    @staticmethod
    def cons(
            view: A,
            layouts: List[Layout],
            tree: ViewTree,
            session: Session,
            window: Window,
    ) -> 'ViewPath':
        return ViewPath(
            view,
            layouts,
            tree,
            session,
            window,
        )

    def __init__(self, view: A, layouts: List[Layout], tree: ViewTree, session: Session, window: Window) -> None:
        self.view = view
        self.layouts = layouts
        self.tree = tree
        self.session = session
        self.window = window


__all__ = ('ViewPath',)
