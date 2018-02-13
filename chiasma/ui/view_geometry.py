from numbers import Number

from amino import Dat, Maybe


class ViewGeometry(Dat['ViewGeometry']):

    @staticmethod
    def cons(
            min_size: Number=None,
            max_size: Number=None,
            fixed_size: Number=None,
            minimized_size: Number=None,
            weight: Number=None,
            position: Number=None,
    ) -> 'ViewGeometry':
        return ViewGeometry(
            Maybe.check(min_size),
            Maybe.check(max_size),
            Maybe.check(fixed_size),
            Maybe.check(minimized_size),
            Maybe.check(weight),
            Maybe.check(position),
        )

    def __init__(
            self,
            min_size: Maybe[Number],
            max_size: Maybe[Number],
            fixed_size: Maybe[Number],
            minimized_size: Maybe[Number],
            weight: Maybe[Number],
            position: Maybe[Number],
    ) -> None:
        self.min_size = min_size
        self.max_size = max_size
        self.fixed_size = fixed_size
        self.minimized_size = minimized_size
        self.weight = weight
        self.position = position


__all__ = ('ViewGeometry',)
