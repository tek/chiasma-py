from amino import Dat, Maybe

from chiasma.util.id import Ident


class Pane(Dat['Pane']):

    @staticmethod
    def cons(
            pane: Ident,
            name: str=None,
            id: str=None,
    ) -> 'Pane':
        return Pane(
            pane,
            name or pane,
            Maybe.check(id),
        )

    def __init__(self, pane: Ident, name: str, id: Maybe[str]) -> None:
        self.pane = pane
        self.name = name
        self.id = id

__all__ = ('Pane',)
