from amino import Dat, Maybe

from chiasma.util.id import Ident, IdentSpec, ensure_ident


class Pane(Dat['Pane']):

    @staticmethod
    def cons(
            ident: IdentSpec,
            id: int=None,
    ) -> 'Pane':
        return Pane(
            ensure_ident(ident),
            Maybe.check(id),
        )

    def __init__(self, ident: Ident, id: Maybe[int]) -> None:
        self.ident = ident
        self.id = id

__all__ = ('Pane',)
