from amino import Dat, Maybe

from chiasma.util.id import Ident, IdentSpec, ensure_ident_or_generate


class Session(Dat['Session']):

    @staticmethod
    def cons(
            ident: IdentSpec,
            id: int=None,
    ) -> 'Session':
        return Session(
            ensure_ident_or_generate(ident),
            Maybe.check(id),
        )

    def __init__(self, ident: Ident, id: Maybe[int]) -> None:
        self.ident = ident
        self.id = id


__all__ = ('Session',)
