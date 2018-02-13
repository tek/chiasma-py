from amino import List, Either, Regex, do, Do, Dat, Right, Try, Left, _, Boolean
from amino.util.numeric import parse_int

from chiasma.io.compute import TmuxIO
from chiasma.command import tmux_data_cmd, TmuxCmdData
from chiasma.data.window import Window
from chiasma.data.pane import Pane
from chiasma.commands.window import window_id


pane_id_re = Regex('^%(?P<id>\d+)$')


@do(Either[str, int])
def parse_pane_id(pane_id: str) -> Do:
    match = yield pane_id_re.match(pane_id)
    id_s = yield match.group('id')
    yield parse_int(id_s)


class PaneData(Dat['PaneData']):

    @staticmethod
    @do(Either[str, 'PaneData'])
    def from_tmux(pane_id: str, pane_width: str, pane_height: str, pane_top: str) -> Do:
        id = yield parse_pane_id(pane_id)
        width = yield parse_int(pane_width)
        height = yield parse_int(pane_height)
        top = yield parse_int(pane_top)
        yield Right(PaneData(id, width, height, top))

    def __init__(self, id: int, width: int, height: int, position: int) -> None:
        self.id = id
        self.width = width
        self.height = height
        self.position = position


class PaneLoc(Dat['PaneLoc']):

    def __init__(self, window_id: str, pane_id: str) -> None:
        self.window_id = window_id
        self.pane_id = pane_id


def parse_pane_data(output: List[str]) -> Either[str, List[PaneData]]:
    return output.traverse(lambda kw: Try(PaneData.from_tmux, **kw).join, Either)


cmd_data_pane = TmuxCmdData.from_cons(PaneData.from_tmux)


def all_panes() -> TmuxIO[List[PaneData]]:
    return tmux_data_cmd('list-panes', List('-a'), cmd_data_pane)


def window_panes(wid: int) -> TmuxIO[List[PaneData]]:
    return tmux_data_cmd('list-panes', List('-t', window_id(wid)), cmd_data_pane)


def pane(session_id: str, window_id: str, pane_id: str) -> Do:
    pass


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
def create_pane_from_data(window: Window, pane: Pane) -> Do:
    window_id = yield TmuxIO.from_maybe(window.id, lambda: f'{window} has no id')
    panes = yield tmux_data_cmd('split-window', List('-t', window_id, '-d', '-P'), cmd_data_pane)
    yield TmuxIO.from_maybe(panes.head, lambda: f'no output when creating pane in {window}')


@do(TmuxIO[Boolean])
def pane_open(id: int) -> Do:
    ps = yield all_panes()
    return ps.contains(_.id == id)


def resize_pane(id: int, vertical: Boolean, size: int) -> TmuxIO[None]:
    direction = '-y' if vertical else '-x'
    return TmuxIO.write('resize-pane', '-t', id, direction, size)


def move_pane(id: int, ref_id: int, vertical: Boolean) -> TmuxIO[None]:
    direction = '-v' if vertical else '-h'
    return TmuxIO.write('move-pane', '-s', id, '-t', ref_id, direction)


__all__ = ('all_panes', 'window_panes', 'pane', 'resize_pane', 'pane_open', 'create_pane_from_data', 'move_pane')
