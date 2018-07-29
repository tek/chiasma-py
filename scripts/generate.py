#!usr/bin/env python3

from amino.meta.gen_state import state_task
from amino import Path, List
from amino.meta.gen import codegen_write

meta_extra = '''\
    def io(self, f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    def delay(self, f: Callable[[Tmux], A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.delay(f))

    def suspend(self, f: Callable[[Tmux], TmuxIO[A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.suspend(f))

    def from_io(self, io: IO[A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.wrap_either(lambda v: io.attempt))

    def from_id(self, st: State[S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.pure(s.value))

    def from_maybe(self, a: Maybe[B], err: CallByName) -> 'TmuxIOState[S, B]':
        return TmuxIOState.lift(TmuxIO.from_maybe(a, err))

    m = from_maybe

    def from_either(self, e: Either[str, A]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.from_either(e))

    e = from_either

    def from_either_state(self, st: EitherState[E, S, A]) -> 'TmuxIOState[S, A]':
        return st.transform_f(TmuxIOState, lambda s: TmuxIO.from_either(s))

    def failed(self, e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.failed(e))

    def error(self, e: str) -> 'TmuxIOState[S, A]':
        return TmuxIOState.lift(TmuxIO.error(e))

    def inspect_maybe(self, f: Callable[[S], Maybe[A]], err: CallByName) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_maybe(f(s), err))

    def inspect_either(self, f: Callable[[S], Either[str, A]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_f(lambda s: TmuxIO.from_either(f(s)))

    def simple(self, f: Callable[..., A], *a: Any, **kw: Any) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.simple(f, *a, **kw))

    def sleep(self, duration: float) -> 'TmuxIOState[S, None]':
        return TS.lift(TmuxIO.sleep(duration))

    def modify_e(self, f: Callable[[S], Either[str, S]]) -> 'TmuxIOState[S, A]':
        return TmuxIOState.inspect_either(f).flat_map(TmuxIOState.set)

    def read(self, cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.read(cmd, *args))

    def write(self, cmd: str, *args: str) -> 'TmuxIOState[S, A]':
        return TS.lift(TmuxIO.write(cmd, *args))
'''

extra = '''
TS = TmuxIOState


class ToTmuxIOState(TypeClass):

    @abc.abstractproperty
    def tmux(self) -> TS:
        ...


class IdStateToTmuxIOState(ToTmuxIOState, tpe=State):

    @tc_prop
    def tmux(self, fa: State[S, A]) -> TS:
        return TmuxIOState.from_id(fa)


class EitherStateToTmuxIOState(ToTmuxIOState, tpe=EitherState):

    @tc_prop
    def tmux(self, fa: EitherState[E, S, A]) -> TS:
        return TmuxIOState.from_either_state(fa)


class TmuxIOToTmuxIOState(ToTmuxIOState, tpe=TmuxIO):

    @tc_prop
    def tmux(self, fa: TmuxIO[A]) -> TS[S, A]:
        return TS.lift(fa)

    @tc_prop
    def state(self, fa: TmuxIO[A]) -> TS[S, A]:
        return self.tmux(fa)
'''

extra_import = List(
    'import abc',
    'from amino.tc.base import TypeClass, tc_prop',
    'from amino.state import State, EitherState',
    'from chiasma.tmux import Tmux',
    'from amino import IO, Maybe, Either',
    'from amino.func import CallByName',
    '''E = TypeVar('E')''',
)
pkg = Path(__file__).absolute().parent.parent
task = state_task('TmuxIO', 'chiasma.io.compute', meta_extra=meta_extra, ctor_extra=meta_extra,
                  extra_import=extra_import, extra=extra)
outpath = pkg / 'chiasma' / 'io' / f'state.py'

codegen_write(task, outpath).fatal
