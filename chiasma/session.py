from amino import do, Do, __
from amino.state import State
from amino.boolean import false

from chiasma.util.id import Ident
from chiasma.data.tmux import TmuxData
from chiasma.io.compute import TmuxIO
from chiasma.commands.session import session_exists, create_session
from chiasma.data.session import Session


@do(State[TmuxData, Session])
def add_session(ident: Ident) -> Do:
    session = Session.cons(ident)
    yield State.pure(session)


@do(State[TmuxData, Session])
def find_or_create_session(ident: Ident) -> Do:
    existing = yield State.inspect(__.session_by_ident(ident))
    session = existing.cata(lambda err: add_session(ident), State.pure)
    yield session


@do(TmuxIO[None])
def ensure_session(session: Session) -> Do:
    exists = yield session.id.map(session_exists) | TmuxIO.pure(false)
    yield TmuxIO.pure(None) if exists else create_session(session.ident)


__all__ = ('add_session', 'find_or_create_session', 'ensure_session')
