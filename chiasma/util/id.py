import re
from uuid import UUID
from typing import Union

from amino import Dat

from amino import Map, Maybe, __
from amino.util.numeric import parse_int


class Key(Dat['Key']):

    def __init__(self, uuid: UUID, name: str) -> None:
        self.uuid = uuid
        self.name = name

    @property
    def _str_extra(self):
        return super()._str_extra.cat(self.name)


Ident = Union[str, UUID, Key]


def parse_id(value, rex, desc):
    return (
        Maybe(rex.match(str(value)))
        .map(__.group(1))
        .map(int)
        .to_either("could not match {} id {}".format(desc, value))
        .or_else(lambda: parse_int(value)))


def amend_options(opt: Map, key: str, value: Maybe):
    return value / (lambda a: opt + (key, a)) | opt

_session_id_re = re.compile('^\$(\d+)$')
_pane_id_re = re.compile('^%(\d+)$')
_win_id_re = re.compile('^@(\d+)$')


def parse_session_id(value):
    return parse_id(value, _session_id_re, 'session')


def parse_window_id(value):
    return parse_id(value, _win_id_re, 'window')


def parse_pane_id(value):
    return parse_id(value, _pane_id_re, 'pane')


__all__ = ('parse_window_id', 'parse_pane_id', 'parse_id', 'Key', 'Ident')
