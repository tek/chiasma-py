import time
import subprocess
from typing import Callable, Any, Tuple

from kallikrein import Expectation, k
from kallikrein.matchers.either import be_right
from kallikrein.matchers.match_with import match_with

from amino import Do, do, Dat, IO
from amino.func import const

from chiasma.test.terminal import start_tmux
from chiasma.test.tmux_spec import tmux_spec_socket
from chiasma.io.state import TS
from chiasma.tmux import Tmux
from chiasma.io.compute import TmuxIO
from chiasma.ui.simple import SimpleViewTree, SimpleLayout
from chiasma.commands.server import kill_server

from unit._support.data import SpecData


class TestConfig(Dat['TestConfig']):

    @staticmethod
    def cons(
            layout: SimpleViewTree=None,
            win_width: int=300,
            win_height: int=120,
            terminal: bool=True,
            socket: str='tmux_spec',
    ) -> 'TestConfig':
        return TestConfig(
            layout or SimpleViewTree.layout(SimpleLayout.cons()),
            win_width,
            win_height,
            terminal,
            socket,
        )

    def __init__(
            self,
            layout: SimpleViewTree,
            win_width: int,
            win_height: int,
            terminal: bool,
            socket: str,
    ) -> None:
        self.layout = layout
        self.win_width = win_width
        self.win_height = win_height
        self.terminal = terminal
        self.socket = socket


def setup_test_tmux(config: TestConfig) -> Tuple[subprocess.Popen, str, Tmux]:
    tmux_proc = start_tmux(config.socket, config.win_width, config.win_height, config.terminal)
    tmux = Tmux.cons(tmux_spec_socket)
    time.sleep(.2)
    cmd = TmuxIO.read('list-clients -F "#{client_name}"')
    tmux_client = cmd.unsafe(tmux).head.get_or_fail('no clients')
    return tmux_proc, tmux_client, tmux


def run_test_io(io: Callable[..., IO[Expectation]], *a: Any, **kw: Any) -> Expectation:
    return k(io(*a, **kw).attempt).must(be_right(match_with(lambda a: a)))


def cleanup(tmux_proc: subprocess.Popen, tmux: Tmux) -> Callable[[Any], IO[None]]:
    @do(IO[None])
    def cleanup(a: Any) -> Do:
        yield IO.delay(tmux_proc.kill).recover(const(None))
        yield IO.delay(tmux_proc.wait).recover(const(None))
        yield IO.delay(kill_server().result, tmux).recover(const(None))
    return cleanup


def unit_test(
        io: Callable[..., TS[SpecData, Expectation]],
        config: TestConfig=TestConfig.cons(),
        *a: Any,
        **kw: Any,
) -> Expectation:
    tmux_proc, tmux_client, tmux = setup_test_tmux(config)
    @do(TmuxIO[Expectation])
    def run() -> Do:
        data = SpecData.cons(config.layout)
        yield io(*a, **kw).run_a(data)
    return run_test_io(TmuxIO.to_io(run(), tmux).ensure, cleanup(tmux_proc, tmux))


__all__ = ('unit_test',)
