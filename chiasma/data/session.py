from amino import Dat, Maybe

from chiasma.util.id import Ident


class Session(Dat['Session']):

    @staticmethod
    def cons(
            ident: Ident,
            id: str=None,
    ) -> None:
        return Session(
            ident,
            Maybe.check(id),
        )

    def __init__(self, ident: Ident, id: Maybe[str]) -> None:
        self.ident = ident
        self.id = id


__all__ = ('Session',)
