from amino import Dat, do, Either, Do, Right, List, Nil, Regex, _, Boolean
from amino.util.numeric import parse_int

from chiasma.io.compute import TmuxIO
from chiasma.command import tmux_data_cmd, TmuxCmdData


session_id_re = Regex('^\$(?P<id>\d+)$')


@do(Either[str, int])
def parse_session_id(session_id: str) -> Do:
    match = yield session_id_re.match(session_id)
    id_s = yield match.group('id')
    yield parse_int(id_s)


def session_id(id: int) -> str:
    return f'${id}'


class SessionData(Dat['SessionData']):

    @staticmethod
    @do(Either[str, 'SessionData'])
    def from_tmux(session_id: str) -> Do:
        id = yield parse_session_id(session_id)
        yield Right(SessionData(id))

    def __init__(self, id: int) -> None:
        self.id = id


cmd_data_session = TmuxCmdData.from_cons(SessionData.from_tmux)


def sessions() -> TmuxIO[List[SessionData]]:
    return tmux_data_cmd('list-sessions', Nil, cmd_data_session)


@do(TmuxIO[Boolean])
def session_exists(id: str) -> Do:
    ss = yield sessions()
    yield Right(ss.exists(_.id == id))


@do(TmuxIO[SessionData])
def create_session(name: str) -> Do:
    sessions = yield tmux_data_cmd('new-session', List('-s', name, '-P'), cmd_data_session)
    yield TmuxIO.from_maybe(sessions.head, f'no output when creating session `{name}`')


__all__ = ('sessions', 'session_exists', 'create_session', 'session_id')
