import inspect
from traceback import FrameSummary
from typing import Any, Tuple

from amino import __, List, Lists, Try, Path
from amino.util.exception import format_exception


def cframe() -> FrameSummary:
    return inspect.currentframe()


def callsite(frame) -> Any:
    def loop(f) -> None:
        pkg = f.f_globals.get('__package__', '')
        mod = f.f_globals.get('__module__', '')
        return loop(f.f_back) if mod == 'chiasma.io.compute' or pkg.startswith('amino') else f
    return loop(frame)


def callsite_info(frame: FrameSummary) -> List[str]:
    cs = callsite(frame)
    source = inspect.getsourcefile(cs.f_code)
    line = cs.f_lineno
    code = Try(Path, source) // (lambda a: Try(a.read_text)) / Lists.lines // __.lift(line - 1) | '<no source>'
    fun = cs.f_code.co_name
    clean = code.strip()
    return List(f'  File "{source}", line {line}, in {fun}', f'    {clean}')


def callsite_source(frame) -> Tuple[List[str], int]:
    cs = callsite(frame)
    source = inspect.getsourcefile(cs.f_code)
    return Try(Path, source) // (lambda a: Try(a.read_text)) / Lists.lines // __.lift(cs.f_lineno - 1) | '<no source>'


class TmuxIOException(Exception):

    def __init__(self, f, stack, cause, frame=None) -> None:
        self.f = f
        self.stack = List.wrap(stack)
        self.cause = cause
        self.frame = frame

    @property
    def lines(self) -> List[str]:
        cause = format_exception(self.cause)
        cs = callsite_info(self.frame)
        return List(f'TmuxIO exception') + cs + cause[-3:]

    def __str__(self):
        return self.lines.join_lines

    @property
    def callsite(self) -> Any:
        return callsite(self.frame)

    @property
    def callsite_source(self) -> List[str]:
        return callsite_source(self.frame)


__all__ = ('TmuxIOException',)
