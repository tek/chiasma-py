import pty
import subprocess

from amino.test import fixture_path


def terminal_args(win_width: int, win_height: int) -> list:
    geom = '{}x{}'.format(win_width + 1, win_height + 1)
    return ['urxvt', '-geometry', geom, '-e']


def start_tmux(socket: str, win_width: int, win_height: int, term: bool=False) -> subprocess.Popen:
    conf = fixture_path('conf', 'tmux.conf')
    t = terminal_args(win_width, win_height) if term else []
    args = t + ['tmux', '-L', socket, '-f', str(conf)]
    master, slave = pty.openpty()
    return subprocess.Popen(args, stdout=slave, stdin=slave, stderr=slave)


__all__ = ('start_tmux',)
