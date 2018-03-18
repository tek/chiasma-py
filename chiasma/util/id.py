import abc

from uuid import UUID, uuid4
from typing import TypeVar, Generic, Any, Type, Union

from amino import Dat
from amino import ADT, Either, List
from amino.json.decoder import Decoder, decode_json_type_json
from amino.json.data import JsonError, Json


class Key(Dat['Key']):

    def __init__(self, uuid: UUID, name: str) -> None:
        self.uuid = uuid
        self.name = name

    @property
    def _str_extra(self):
        return super()._str_extra.cat(self.name)


A = TypeVar('A')


class Ident(Generic[A], ADT['Ident']):

    @staticmethod
    def generate() -> 'Ident':
        return UUIDIdent(uuid4())

    def __init__(self, value: A) -> None:
        self.value = value

    @abc.abstractproperty
    def str(self) -> str:
        ...


class StrIdent(Ident[str]):

    @property
    def str(self) -> str:
        return self.value


class UUIDIdent(Ident[UUID]):

    @property
    def str(self) -> str:
        return str(self.value)


class KeyIdent(Ident[Key]):

    @property
    def str(self) -> str:
        return self.value.name


def decode_uuid_ident(data: Json) -> Either[JsonError, UUIDIdent]:
    return decode_json_type_json(data, UUID) / UUIDIdent


def decode_str_ident(data: Json) -> Either[JsonError, StrIdent]:
    return decode_json_type_json(data, str) / StrIdent


class IdentDecoder(Decoder, tpe=Ident):

    def decode(self, tpe: Type[Ident], data: Json) -> Either[JsonError, Ident[Any]]:
        return (
            decode_json_type_json(data, Key).lmap(List)
            .accum_error_lift(decode_uuid_ident, data)
            .accum_error_lift(decode_str_ident, data)
        )


IdentSpec = Union[Ident, str, UUID, Key, None]


def ensure_ident(spec: IdentSpec) -> Ident:
    return (
        spec
        if isinstance(spec, Ident) else
        UUIDIdent(spec)
        if isinstance(spec, UUID) else
        StrIdent(spec)
        if isinstance(spec, str) else
        KeyIdent(spec)
        if isinstance(spec, Key) else
        Ident.generate()
    )


__all__ = ('Ident', 'Key', 'StrIdent', 'UUIDIdent', 'KeyIdent', 'IdentSpec', 'ensure_ident')
