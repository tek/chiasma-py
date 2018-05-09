from amino import do, IO, List, Do, Lists

from psutil import Process

from chiasma.commands.pane import PaneData, all_panes
from chiasma.io.compute import TmuxIO


@do(IO[List[int]])
def child_pids(pid: int) -> Do:
    proc = yield IO.delay(Process, pid)
    children = yield IO.delay(proc.children, recursive=True)
    yield IO.delay(Lists.wrap(children).map, lambda a: a.pid)


@do(IO[bool])
def contains_child_pid(target_pid: int, pane_data: PaneData) -> Do:
    pids = yield child_pids(pane_data.pid)
    return pids.contains(target_pid)


@do(TmuxIO[PaneData])
def discover_pane_by_pid(target_pid: int) -> Do:
    panes = yield all_panes()
    indicators = yield TmuxIO.from_io(panes.traverse(lambda a: contains_child_pid(target_pid, a), IO))
    candidate = panes.zip(indicators).find_map(lambda a: a[1].m(a[0]))
    yield TmuxIO.from_maybe(candidate, f'could not find pane with pid `{target_pid}`')


__all__ = ('child_pids', 'contains_child_pid', 'discover_pane_by_pid',)
