import abc
from subprocess import Popen, PIPE

from amino import List, Lists, Map, Boolean, do, Either, Do, _, __, Try, Dat, ADT, Nil, Maybe
from amino.boolean import false, true
from amino.string.hues import blue, red

from amino.logging import Logging
from amino.case import Case

from chiasma.data.session import Session
from chiasma.data.window import Window
from chiasma.data.pane import Pane


class POutput(ADT['POutput']):

    def __init__(self, output: List[str]) -> None:
        self.output = output


class PSuccess(POutput):
    pass


class PError(POutput):
    pass


class TmuxCmd(Dat['TmuxCmd']):

    def __init__(self, cmd: str, args: List[str]) -> None:
        self.cmd = cmd
        self.args = args

    @property
    def cmdline(self) -> str:
        return self.args.cons(self.cmd).join_tokens


class TmuxCmdResult(ADT['TmuxCmdResult']):
    pass


class TmuxCmdSuccess(TmuxCmdResult):

    def __init__(self, cmd: TmuxCmd, output: PSuccess) -> None:
        self.cmd = cmd
        self.output = output


class TmuxCmdError(TmuxCmdResult):

    def __init__(self, cmd: TmuxCmd, output: PError) -> None:
        self.cmd = cmd
        self.output = output


class TmuxCmdFatal(TmuxCmdResult):

    def __init__(self, cmds: List[TmuxCmd], output: PError) -> None:
        self.cmds = cmds
        self.output = output


class PState(Dat['PState']):

    def __init__(self, in_cmd: Boolean, current: List[str], cmds: List[POutput]) -> None:
        self.in_cmd = in_cmd
        self.current = current
        self.cmds = cmds

    def push(self, output: POutput) -> 'PState':
        return self.append1.cmds(output).set.current(Nil).set.in_cmd(false)

    def success(self) -> 'PState':
        return self.push(PSuccess(self.current))

    def error(self) -> 'PState':
        return self.push(PError(self.current))


def parse_cmd_output(output: List[str]) -> List[str]:
    def parse(z: PState, a: str) -> PState:
        return (
            z.set.in_cmd(true)
            if a.startswith('%begin') else
            z.success()
            if a.startswith('%end') else
            z.error()
            if a.startswith('%error') else
            z.append1.current(a)
            if z.in_cmd else
            z
        )
    return output.fold_left(PState(false, Nil, Nil))(parse).cmds.drop(1)


class create_cmd_result(Case, alg=POutput):

    def __init__(self, cmd: TmuxCmd) -> None:
        self.cmd = cmd

    def p_success(self, output: PSuccess) -> TmuxCmdResult:
        return TmuxCmdSuccess(self.cmd, output)

    def p_error(self, output: PError) -> TmuxCmdResult:
        return TmuxCmdError(self.cmd, output)


def create_cmd_results(cmds: List[TmuxCmd], output: List[str]) -> List[TmuxCmdResult]:
    return cmds.zip(parse_cmd_output(output)).map2(lambda c, o: create_cmd_result(c)(o))


class Tmux(Logging, abc.ABC):

    @staticmethod
    def cons(socket: str=None) -> 'Tmux':
        return NativeTmux(Maybe.optional(socket))

    @abc.abstractmethod
    def execute_cmds(self, cmds: List[TmuxCmd]) -> List[TmuxCmdResult]:
        ...


class NativeTmux(Tmux):

    def __init__(self, socket: Maybe[str]) -> None:
        self.socket = socket

    def execute_cmds(self, cmds: List[TmuxCmd]) -> List[TmuxCmdResult]:
        socket_args = self.socket / (lambda a: ['-L', a]) | []
        proc = Popen(args=['tmux'] + socket_args + ['-C', 'attach'], stdin=PIPE, stdout=PIPE, stderr=PIPE,
                     universal_newlines=True)
        cmdlines = (cmds / _.cmdline).cat('').join_lines
        stdout, stderr = proc.communicate(cmdlines)
        results = create_cmd_results(cmds, Lists.lines(stdout))
        return (
            List(TmuxCmdFatal(cmds, PError(Lists.lines(stderr))))
            if proc.returncode == 0 and results.empty else
            results
        )


class PureTmux(Tmux):

    def __init__(self, _sessions: List[Session], _windows: List[Window], _panes: List[Pane]) -> None:
        self._sessions = _sessions
        self._windows = _windows
        self._panes = _panes

    def execute_cmds(self, cmds: List[TmuxCmd]) -> List[TmuxCmdResult]:
        return Nil

__all__ = ('Tmux',)
