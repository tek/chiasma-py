from amino import do, Do, __, Just
from amino.state import State
from amino.boolean import false

from chiasma.util.id import Ident
from chiasma.data.tmux import Views
from chiasma.io.compute import TmuxIO
from chiasma.commands.session import session_exists, create_session
from chiasma.data.session import Session
from chiasma.io.state import TS


@do(State[Views, Session])
def add_session(ident: Ident) -> Do:
    session = Session.cons(ident)
    yield State.pure(session)


@do(State[Views, Session])
def find_or_create_session(ident: Ident) -> Do:
    existing = yield State.inspect(__.session_by_ident(ident))
    session = existing.cata(lambda err: add_session(ident), State.pure)
    yield session


@do(TS[Views, Session])
def create_and_update_session(session: Session) -> Do:
    session_data = yield TS.lift(create_session(session.ident.str))
    updated_session = session.set.id(Just(session_data.id))
    yield TS.modify(__.update_session(updated_session))
    return updated_session


@do(TS[Views, Session])
def ensure_session(session: Session) -> Do:
    exists = yield TS.lift(session.id.map(session_exists) | TmuxIO.pure(false))
    yield TS.pure(session) if exists else create_and_update_session(session)


__all__ = ('add_session', 'find_or_create_session', 'ensure_session')
