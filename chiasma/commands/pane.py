from amino import List, Either, Regex, do, Do, Dat, Right, Try, Left, Boolean, L, Lists, _, Path, IO
from amino.util.numeric import parse_int
from amino.logging import module_log

from chiasma.io.compute import TmuxIO
from chiasma.command import tmux_data_cmd, TmuxCmdData, simple_tmux_cmd_attr
from chiasma.data.window import Window
from chiasma.data.pane import Pane
from chiasma.commands.window import window_id, parse_window_id
from chiasma.commands.session import parse_session_id
from chiasma.ui.view import UiPane

log = module_log()
pane_id_re = Regex('^%(?P<id>\d+)$')


@do(Either[str, int])
def parse_pane_id(pane_id: str) -> Do:
    match = yield pane_id_re.match(pane_id)
    id_s = yield match.group('id')
    yield parse_int(id_s)


@do(Either[str, bool])
def parse_bool(data: str) -> Do:
    as_int = yield parse_int(data)
    yield (
        Right(as_int == 1)
        if as_int in [0, 1] else
        Left(f'invalid number for boolean: {as_int}')
    )


def pane_id(id: int) -> str:
    return f'%{id}'


class PaneData(Dat['PaneData']):

    @staticmethod
    @do(Either[str, 'PaneData'])
    def from_tmux(
            pane_id: str,
            pane_width: str,
            pane_height: str,
            pane_top: str,
            pane_pid: str,
            window_id: str,
            session_id: str,
    ) -> Do:
        id = yield parse_pane_id(pane_id)
        width = yield parse_int(pane_width)
        height = yield parse_int(pane_height)
        top = yield parse_int(pane_top)
        pid = yield parse_int(pane_pid)
        wid = yield parse_window_id(window_id)
        sid = yield parse_session_id(session_id)
        yield Right(PaneData(id, width, height, top, pid, wid, sid))

    def __init__(
            self,
            id: int,
            width: int,
            height: int,
            position: int,
            pid: int,
            window_id: int,
            session_id: int,
    ) -> None:
        self.id = id
        self.width = width
        self.height = height
        self.position = position
        self.pid = pid
        self.window_id = window_id
        self.session_id = session_id


class PaneLoc(Dat['PaneLoc']):

    def __init__(self, window_id: str, pane_id: str) -> None:
        self.window_id = window_id
        self.pane_id = pane_id


def parse_pane_data(output: List[str]) -> Either[str, List[PaneData]]:
    return output.traverse(lambda kw: Try(PaneData.from_tmux, **kw).join, Either)


def pane_cmd(id: int, cmd: str, *args: str) -> List[str]:
    return List(cmd, '-t', pane_id(id)) + Lists.wrap(args)


cmd_data_pane = TmuxCmdData.from_cons(PaneData.from_tmux)


def all_panes() -> TmuxIO[List[PaneData]]:
    return tmux_data_cmd('list-panes', List('-a'), cmd_data_pane)


def window_panes(wid: int) -> TmuxIO[List[PaneData]]:
    return tmux_data_cmd('list-panes', List('-t', window_id(wid)), cmd_data_pane)


@do(TmuxIO[PaneData])
def window_pane(wid: int, pane_id: int) -> Do:
    panes = yield window_panes(wid)
    yield TmuxIO.from_maybe(panes.find(_.id == pane_id), f'no pane with id `{pane_id}`')


@do(TmuxIO[PaneData])
def pane(pane_id: int) -> Do:
    panes = yield all_panes()
    yield TmuxIO.from_maybe(panes.find(_.id == pane_id), f'no pane with id `{pane_id}`')


@do(TmuxIO[int])
def pane_width(id: int) -> Do:
    p = yield pane(id)
    return p.width


@do(TmuxIO[int])
def pane_height(id: int) -> Do:
    p = yield pane(id)
    return p.height


@do(Either[str, PaneLoc])
def pane_loc(window: Window, pane: Pane) -> Do:
    window_id = yield window.id.to_either(lambda: f'{window} has no id')
    pane_id = yield pane.id.to_either(lambda: f'{pane} has no id')
    return PaneLoc(window_id, pane_id)


@do(TmuxIO[Either[str, PaneData]])
def pane_from_loc(loc: PaneLoc) -> Do:
    panes = yield window_panes(loc.window_id)
    return panes.find(_.id == loc.pane_id).to_either(lambda: f'no pane with id {loc.pane_id} in window {loc.window_id}')


@do(TmuxIO[Either[str, PaneData]])
def pane_from_data(window: Window, pane: Pane) -> Do:
    yield (pane_loc(window, pane) / pane_from_loc).value_or(lambda e: TmuxIO.pure(Left(e)))


@do(TmuxIO[PaneData])
def create_pane_from_data(window: Window, pane: Pane, dir: Path) -> Do:
    target_window = yield TmuxIO.from_maybe(window.id, lambda: f'{window} has no id')
    args = List('-t', window_id(target_window), '-d', '-P', '-c', dir)
    panes = yield tmux_data_cmd('split-window', args, cmd_data_pane)
    yield TmuxIO.from_maybe(panes.head, lambda: f'no output when creating pane in {window}')


@do(TmuxIO[Boolean])
def pane_open(id: int) -> Do:
    ps = yield all_panes()
    return ps.exists(_.id == id)


@do(TmuxIO[Boolean])
def window_pane_open(wid: int, id: int) -> Do:
    ps = yield window_panes(wid)
    return ps.exists(_.id == id)


def resize_pane(id: int, vertical: Boolean, size: int) -> TmuxIO[None]:
    direction = '-y' if vertical else '-x'
    return TmuxIO.write('resize-pane', '-t', pane_id(id), direction, size)


def move_pane(id: int, ref_id: int, vertical: Boolean) -> TmuxIO[None]:
    direction = '-v' if vertical else '-h'
    return TmuxIO.write('move-pane', '-d', '-s', pane_id(id), '-t', pane_id(ref_id), direction)


def close_pane_id(pane_id: int) -> TmuxIO[None]:
    return TmuxIO.write(*pane_cmd(pane_id, 'kill-pane'))


def close_pane(pane: PaneData) -> TmuxIO[None]:
    log.debug(f'closing pane {pane}')
    return close_pane_id(pane.id)


def quote(data: str) -> str:
    escaped = data.replace('"', '\\"')
    return f'"{escaped}"'


def send_keys(id: int, lines: List[str]) -> TmuxIO[None]:
    with_crs = lines.map(quote).flat_map(L(List)(_, 'enter'))
    return with_crs.traverse(L(TmuxIO.write)('send-keys', '-t', pane_id(id), _), TmuxIO)


@do(TmuxIO[str])
def capture_pane(id: int) -> Do:
    output = yield TmuxIO.read(*pane_cmd(id, 'capture-pane', '-p'))
    yield TmuxIO.pure(output.reversed.drop_while(_ == '').reversed)


pipe_filter = """sed -u -e 's/\x1b\[[0-9\;?]*[mlK]//g' | sed -u -e 's/\r//g'"""


def pipe_pane(id: int, path: Path) -> TmuxIO[None]:
    return TmuxIO.write(*pane_cmd(id, 'pipe-pane', quote(f'{pipe_filter} > {str(path)}')))


@do(TmuxIO[int])
def pane_pid(id: int) -> Do:
    p = yield pane(id)
    return p.pid


def select_pane(id: int) -> TmuxIO[int]:
    return TmuxIO.write(*pane_cmd(id, 'select-pane'))


__all__ = ('all_panes', 'window_panes', 'pane', 'resize_pane', 'pane_open', 'create_pane_from_data', 'move_pane',
           'close_pane', 'send_keys', 'capture_pane', 'window_pane', 'close_pane_id', 'pane_width', 'pane_height',
           'pane_pid', 'window_pane_open', 'select_pane',)
