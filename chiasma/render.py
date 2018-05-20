from typing import TypeVar

from amino.tc.context import context, Bindings
from amino import do, Do
from amino.logging import module_log

from chiasma.window.main import pack_window, find_or_create_window, ensure_window, ensure_view, window_state
from chiasma.data.tmux import Views
from chiasma.util.id import Ident
from chiasma.data.view_tree import ViewTree
from chiasma.session import find_or_create_session, ensure_session
from chiasma.window.principal import principal_pane
from chiasma.io.state import TS

log = module_log()
LO = TypeVar('LO')
P = TypeVar('P')


@context(**pack_window.bounds)
@do(TS[Views, None])
def render(bindings: Bindings, session_ident: Ident, window_ident: Ident, layout: ViewTree[LO, P]) -> Do:
    log.debug(f'rendering window {window_ident}')
    session = yield find_or_create_session(session_ident).tmux
    window = yield find_or_create_window(window_ident).tmux
    updated_session = yield ensure_session(session)
    yield ensure_window(updated_session, window, window_ident, layout)
    yield ensure_view(updated_session, window)(layout)
    ui_princ, t_princ = yield principal_pane(layout)
    ws = yield window_state(window_ident, window, layout)
    yield pack_window(bindings)(updated_session, window, ui_princ)(ws)


__all__ = ('render',)
