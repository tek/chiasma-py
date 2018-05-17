from typing import TypeVar, Callable, Generic
import inspect

from amino import List, Either, Map, Lists, do, Do, _, L, Try, Dat, Maybe

from chiasma.io.compute import TmuxIO


def tmux_fmt_attr(attr: str) -> str:
    return f'#{{{attr}}}'


def tmux_fmt_attrs(attrs: List[str]) -> str:
    raw = (attrs / tmux_fmt_attr).join_tokens
    return f"'{raw}'"


def tmux_attr_map(attrs: List[str], output: str) -> Map[str, str]:
    tokens = Lists.split(output, ' ')
    return Map(attrs.zip(tokens))


A = TypeVar('A')


class TmuxCmdData(Generic[A], Dat['TmuxCmdData[A]']):

    @staticmethod
    def from_cons(cons: Callable[..., A]) -> 'TmuxCmdData[A]':
        f = getattr(cons, '__do_original', cons)
        spec = inspect.getfullargspec(f)
        return TmuxCmdData(Lists.wrap(spec.args), cons)

    def __init__(self, attrs: List[str], cons: Callable[..., A]) -> None:
        self.attrs = attrs
        self.cons = cons


@do(TmuxIO[List[Map[str, str]]])
def simple_tmux_cmd_attrs(cmd: str, args: List[str], attrs: List[str]) -> Do:
    output = yield TmuxIO.read(cmd, '-F', tmux_fmt_attrs(attrs), *args)
    yield TmuxIO.pure(output / L(tmux_attr_map)(attrs, _))


@do(TmuxIO[List[str]])
def simple_tmux_cmd_attr(cmd: str, args: List[str], attr: str) -> Do:
    attrs = yield simple_tmux_cmd_attrs(cmd, args, List(attr))
    yield TmuxIO.from_maybe(attrs.traverse(lambda a: a.lift(attr), Maybe), f'attr `{attr}` missing in output')


def cons_tmux_data(data: List[Map[str, str]], cons: Callable[..., Either[str, A]]) -> Either[str, A]:
    return data.traverse(lambda kw: Try(cons, **kw).join, Either)


@do(TmuxIO[A])
def tmux_data_cmd(cmd: str, args: List[str], cmd_data: TmuxCmdData[A]) -> Do:
    data = yield simple_tmux_cmd_attrs(cmd, args, cmd_data.attrs)
    yield TmuxIO.from_either(cons_tmux_data(data, cmd_data.cons))


__all__ = ('tmux_data_cmd', 'TmuxCmdData')
