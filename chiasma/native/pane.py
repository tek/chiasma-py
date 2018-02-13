import abc

from psutil import Process

from amino import __, List, Maybe, Map, Either, Try, _, Dat
from amino.lazy import lazy

from chiasma.util.id import parse_int
from chiasma.util.id import parse_pane_id, parse_window_id, parse_session_id


def child_pids(root: int) -> Either[Exception, List[int]]:
    return (
        Try(Process, root) /
        __.children() /
        List.wrap /
        __.map(_.pid)
    )


def descendant_pids(root: int) -> Either[Exception, List[int]]:
    def recurse(pids: List[int]) -> Either[Exception, List[int]]:
        return pids.traverse(descendant_pids, Either) / _.join / pids.add
    return child_pids(root) // recurse


__all__ = ('PaneData',)
