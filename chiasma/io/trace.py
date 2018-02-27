from amino import List, Maybe, Just
from amino.io import IOExceptionBase
from amino.util.trace import default_internal_packages


class TmuxIOException(IOExceptionBase):

    @property
    def desc(self) -> str:
        return 'TmuxIO exception'

    @property
    def internal_packages(self) -> Maybe[List[str]]:
        return Just(default_internal_packages.cons('chiasma.io'))


__all__ = ('TmuxIOException',)
