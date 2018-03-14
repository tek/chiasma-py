from uuid import UUID, uuid4
from typing import TypeVar, Generic, Any, Type

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


class StrIdent(Ident[str]):
    pass


class UUIDIdent(Ident[UUID]):
    pass


class KeyIdent(Ident[Key]):
    pass


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


__all__ = ('Ident', 'Key', 'StrIdent', 'UUIDIdent', 'KeyIdent')
