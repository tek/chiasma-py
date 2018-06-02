from typing import TypeVar, Generic, Callable, Tuple

from amino.case import Case
from amino import Either, ADT, Right, Left, Dat, Nil, List
from amino.func import const

from chiasma.data.view_tree import ViewTree, LayoutNode, PaneNode, SubUiNode
from chiasma.util.id import Ident, IdentSpec, ensure_ident_or_generate

L = TypeVar('L')
P = TypeVar('P')


class ModPaneResult(Generic[L, P], ADT['ModPaneResult[L, P]']):
    pass


class Found(ModPaneResult[L, P]):

    def __init__(self, tree: ViewTree[L, P]) -> None:
        self.tree = tree


class FoundHere(ModPaneResult[L, P]):

    def __init__(self, pane: PaneNode[L, P]) -> None:
        self.pane = pane


class NotFound(ModPaneResult[L, P]):

    def __init__(self, tree: ViewTree[L, P]) -> None:
        self.tree = tree


class ModPaneFuncs(Generic[L, P], Dat['ModPaneFuncs[L, P]']):

    @staticmethod
    def cons(
            thunk: Callable[[PaneNode[L, P]], Either[str, PaneNode[L, P]]],
            layout: Callable[[LayoutNode[L, P], List[ModPaneResult[L, P]]], Either[str, LayoutNode[L, P]]]=None,
    ) -> 'ModPaneFuncs[L, P]':
        return ModPaneFuncs(thunk, layout or (lambda l, r: Right(l)))

    def __init__(
            self,
            thunk: Callable[[PaneNode[L, P]], Either[str, PaneNode[L, P]]],
            layout: Callable[[LayoutNode[L, P], List[ModPaneResult[L, P]]], Either[str, LayoutNode[L, P]]],
    ) -> None:
        self.thunk = thunk
        self.layout = layout


class LayoutModPaneState(Dat['LayoutModPaneState']):

    @staticmethod
    def cons(
            sub: List[ViewTree[L, P]]=Nil,
            results: List[ModPaneResult[L, P]]=Nil,
            found: bool=False,
    ) -> 'LayoutModPaneState':
        return LayoutModPaneState(
            sub,
            results,
            found,
        )

    def __init__(self, sub: List[ViewTree[L, P]], results: List[ModPaneResult[L, P]], found: bool) -> None:
        self.sub = sub
        self.results = results
        self.found = found


# TODO generalize for layouts
# could use the `layout` modder result like the on for panes
# return Found only if `layout` returns `Right`, then it can be used by the parent layout like pane results
class mod_pane_step(Generic[L, P], Case[ViewTree[L, P], ModPaneResult[L, P]], alg=ViewTree):

    def __init__(self, funcs: ModPaneFuncs) -> None:
        self.funcs = funcs

    def layout(self, a: LayoutNode[L, P]) -> ModPaneResult[L, P]:
        state = a.sub.fold_left(LayoutModPaneState.cons())(layout_sub_step(self))
        new_tree = a.set.sub(state.sub)
        final_tree = self.funcs.layout(new_tree, state.results).get_or_strict(new_tree)
        return Found(final_tree) if state.found else NotFound(final_tree)

    def pane(self, a: PaneNode[L, P]) -> ModPaneResult[L, P]:
        return self.funcs.thunk(a).cata(
            const(NotFound(a)),
            FoundHere,
        )

    def sub_ui(self, a: SubUiNode[L, P]) -> ModPaneResult[L, P]:
        pass


class layout_sub_result(Case[ModPaneResult[L, P], Tuple[ViewTree[L, P], bool]], alg=ModPaneResult):

    def found(self, a: Found[L, P]) -> Tuple[ViewTree[L, P], bool]:
        return a.tree, True

    def found_here(self, a: FoundHere[L, P]) -> Tuple[ViewTree[L, P], bool]:
        return a.pane, True

    def not_found(self, a: NotFound[L, P]) -> Tuple[ViewTree[L, P], bool]:
        return a.tree, False


def layout_sub_step(step: mod_pane_step[L, P]) -> Callable[[LayoutModPaneState, ViewTree[L, P]], LayoutModPaneState]:
    def layout_sub_step(z: LayoutModPaneState, a: ViewTree[L, P]) -> LayoutModPaneState:
        result = step(a)
        tree, found = layout_sub_result.match(result)
        return z.append1.sub(tree).append1.results(result).mod.found(lambda a: a or found)
    return layout_sub_step


class mod_pane_result(Case[ModPaneResult[L, P], Either[str, ViewTree[L, P]]], alg=ModPaneResult):

    def found(self, a: Found[L, P]) -> Either[str, ViewTree[L, P]]:
        return Right(a.tree)

    def found_here(self, a: FoundHere[L, P]) -> Either[str, ViewTree[L, P]]:
        return Left('mod_pane_result called with a PaneNode')

    def not_found(self, a: NotFound[L, P]) -> Either[str, ViewTree[L, P]]:
        return Left(f'no matching pane found')


def mod_pane(
        thunk: Callable[[PaneNode[L, P]], Either[str, PaneNode[L, P]]],
        layout: Callable[[LayoutNode[L, P], ModPaneResult[L, P]], Either[str, LayoutNode[L, P]]]=None,
) -> Callable[[ViewTree[L, P]], Either[str, ViewTree[L, P]]]:
    def mod_pane(tree: ViewTree[L, P]) -> Either[str, ViewTree[L, P]]:
        result = mod_pane_step(ModPaneFuncs.cons(thunk, layout))(tree)
        return mod_pane_result.match(result)
    return mod_pane


def match_ident(spec: IdentSpec) -> Callable[[ViewTree[L, P]], bool]:
    ident = ensure_ident_or_generate(spec)
    def match_ident(tree: ViewTree[L, P]) -> bool:
        return tree.data.ident == ident
    return match_ident


__all__ = ('mod_pane',)
