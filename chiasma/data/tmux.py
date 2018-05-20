from amino import Dat, List, Nil, Either, _, Just
from amino.lenses.lens import lens

from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.data.pane import Pane
from chiasma.util.id import Ident


class Views(Dat['Views']):

    @staticmethod
    def cons(
            sessions: List[Session]=Nil,
            windows: List[Window]=Nil,
            panes: List[Pane]=Nil,
    ) -> 'Views':
        return Views(
            sessions,
            windows,
            panes,
        )

    def __init__(
            self,
            sessions: List[Session],
            windows: List[Window],
            panes: List[Pane],
    ) -> None:
        self.sessions = sessions
        self.windows = windows
        self.panes = panes

    def update_session(self, session: Session) -> 'Views':
        return lens.sessions.Each().Filter(_.ident == session.ident).set(session)(self)

    def add_pane(self, pane: Pane) -> 'Views':
        return self.append1.panes(pane)

    def update_pane(self, pane: Pane) -> 'Views':
        return lens.panes.Each().Filter(_.ident == pane.ident).set(pane)(self)

    def set_pane_id(self, pane: Pane, id: str) -> 'Views':
        return self.update_pane(pane.copy(id=Just(id)))

    def session_by_ident(self, ident: Ident) -> Either[str, Session]:
        return self.sessions.find(_.ident == ident).to_either(f'no session for `{ident}`')

    def window_by_ident(self, ident: Ident) -> Either[str, Window]:
        return self.windows.find(_.ident == ident).to_either(f'no window for `{ident}`')

    def pane_by_ident(self, ident: Ident) -> Either[str, Pane]:
        return self.panes.find(_.ident == ident).to_either(lambda: f'no pane for `{ident}`')


__all__ = ('Views',)
