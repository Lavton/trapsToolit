from abc import ABCMeta, abstractmethod
from typing import Tuple

from .abstract_trap import AbstractCylCoordinateCell
from .utils import PhysicalBorder, Dimention


class CylinderTrap(AbstractCylCoordinateCell, metaclass=ABCMeta):
    """создание цилиндрической ловушки"""
    def __init__(self, R: Dimention, z0: Dimention, thickness=None, closed=True):
        super(CylinderTrap, self).__init__()
        self.closed = closed
        self.R = R
        self.z0 = z0
        self._z_full = z0  # полу-длина ловушки. Не всегда это z0. Ибо часто z0 -- рабочая область, а не вся
        self.thickness = thickness  # толщина стенок в относительных величинах
        self.model_delta = 2 * thickness if thickness else 0.2  # граница рабочей области (дельта + длина)
        self.border = PhysicalBorder(
            x=self.R * (1 + self.model_delta),
            y=self.R * (1 + self.model_delta),
            z=self._z_full * (1 + self.model_delta)
        )

    def is_point_is_in_an_electrode(self, r, theta, z):
        if self.is_endcap_electrode(r, theta, z):
            return True
        if abs(z) < self._z_full:
            if self.R <= r and (not self.thickness or r < self.R * (1+self.thickness)):
                return True
        return False

    def is_endcap_electrode(self, r, theta, z):
        if not self.closed:
            return False
        z = abs(z)
        if self._z_full <= z and (not self.thickness or z < self._z_full * (1+self.thickness)):
            return True
        return False
