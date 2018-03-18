from amino import Dat

from chiasma.util.id import Ident


class Layout(Dat['Layout']):

    @staticmethod
    def cons(
        ident: Ident,
    ) -> 'Layout':
        return Layout(
            ident,
        )

    def __init__(self, ident: Ident) -> None:
        self.ident = ident


__all__ = ('Layout',)
