from amino import Dat, Maybe

from chiasma.util.id import Ident


class Window(Dat['Window']):

    @staticmethod
    def cons(
            ident: Ident,
            id: int=None,
    ) -> 'Window':
        return Window(
            ident,
            Maybe.check(id),
        )

    def __init__(self, ident: Ident, id: Maybe[int]) -> None:
        self.ident = ident
        self.id = id


__all__ = ('Window',)
