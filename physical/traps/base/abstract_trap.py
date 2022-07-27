from abc import ABCMeta, abstractmethod, abstractproperty
from typing import Tuple, Optional

from ....physical.electodes.base.electrode_conf import ElectrodeType, ElectrodeConfiguration
from ....physical.traps.base.utils import PhysicalBorder


class AbstractCylCoordinateCell(metaclass=ABCMeta):
    """абстрактная ловушка в цилиндрической системе координат"""
    @abstractmethod
    def is_point_is_in_an_electrode(self, r, theta, z) -> bool:
        """находится ли точка в каком-то электроде"""
        pass

    @abstractmethod
    def get_electrode_type_when_electrode(self, r, theta, z) -> ElectrodeType:
        pass

    def get_electrode_type_from_point(self, r, theta, z) -> Optional[ElectrodeType]:
        """потенциал ловушки в точке (для тех ловушек, где это имеет смысл)"""
        if self.is_point_is_in_an_electrode(r, theta, z):
            return self.get_electrode_type_when_electrode(r, theta, z)
        return None

    border: PhysicalBorder
    electrodeConfiguration: ElectrodeConfiguration

    def __init__(self):
        self.electrodeConfiguration = ElectrodeConfiguration()
