from typing import TypeVar

from amino.test.spec import SpecBase

from chiasma.test.terminal import start_tmux
from chiasma.io.compute import TmuxIO
from chiasma.commands.server import kill_server
from chiasma.tmux import Tmux
from chiasma.io.state import TS

D = TypeVar('D')
tmux_spec_socket = 'tmux_spec'


class TmuxSpec(SpecBase):

    def __init__(self) -> None:
        self.win_width = 300
        self.win_height = 120

    def tmux_in_terminal(self) -> bool:
        return True

    def setup(self) -> None:
        self.tmux_proc = start_tmux(tmux_spec_socket, self.win_width, self.win_height, self.tmux_in_terminal())
        self.tmux = Tmux.cons(tmux_spec_socket)
        self._wait(.2)
        cmd = TmuxIO.read('list-clients -F "#{client_name}"')
        self.tmux_client = cmd.unsafe(self.tmux).head.get_or_fail('no clients')

    def teardown(self) -> None:
        self.tmux_proc.kill()
        self.tmux_proc.wait()
        kill_server().result(self.tmux)

    def run(self, prog: TS[D, None], data: D) -> None:
        self._wait(.2)
        r = prog.run(data).unsafe(self.tmux)
        TmuxIO.write('display-panes', '-t', self.tmux_client).result(self.tmux)
        self._wait(.2)
        return r


__all__ = ('TmuxSpec', 'tmux_spec_socket')
