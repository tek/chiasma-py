from amino import Dat, Maybe, Nil, List

from chiasma.util.id import Ident
from chiasma.data.pane import Pane


class Window(Dat['Window']):

    @staticmethod
    def cons(
            window: Ident,
            name: str=None,
            id: int=None,
            panes: List[Pane]=Nil,
    ) -> 'Window':
        return Window(
            window,
            name or window,
            Maybe.check(id),
            panes,
        )

    def __init__(self, window: Ident, name: str, id: Maybe[int], panes: List[Pane]) -> None:
        self.window = window
        self.name = name
        self.id = id
        self.panes = panes


__all__ = ('Window',)
