import abc
from typing import Generic, TypeVar

from amino import ADT, Either, Right, Left

A = TypeVar('A')


class TResult(Generic[A], ADT['TmuxIOResult[A]']):

    @abc.abstractproperty
    def to_either(self) -> Either[Exception, A]:
        ...


class TSuccess(Generic[A], TResult[A]):

    def __init__(self, value: A) -> None:
        self.value = value

    @property
    def to_either(self) -> Either[Exception, A]:
        return Right(self.value)


class TError(Generic[A], TResult[A]):

    def __init__(self, error: str) -> None:
        self.error = error

    @property
    def to_either(self) -> Either[Exception, A]:
        return Left(Exception(self.error))


class TFatal(Generic[A], TResult[A]):

    def __init__(self, exception: Exception) -> None:
        self.exception = exception

    @property
    def to_either(self) -> Either[Exception, A]:
        return Left(self.exception)


__all__ = ('TResult', 'TSuccess', 'TError', 'TFatal')
