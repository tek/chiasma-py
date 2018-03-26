from amino import Dat

from chiasma.util.id import Ident, IdentSpec, ensure_ident


class Layout(Dat['Layout']):

    @staticmethod
    def cons(
        ident: IdentSpec,
    ) -> 'Layout':
        return Layout(
            ensure_ident(ident),
        )

    def __init__(self, ident: Ident) -> None:
        self.ident = ident


__all__ = ('Layout',)
