from amino import Boolean, Dat


class ViewState(Dat['ViewState']):

    @staticmethod
    def cons(minimized: bool=False) -> 'ViewState':
        return ViewState(Boolean(minimized))

    def __init__(self, minimized: Boolean) -> None:
        self.minimized = minimized

__all__ = ('ViewState',)
