from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


class Grid3DParams:
    """
    класс для работы с 3D сеткой
    """
    @dataclass
    class MirrorDirection:
        x: bool = False
        y: bool = False
        z: bool = False

        @classmethod
        def create_from_str(cls, str_mirror: str):
            return cls(
                x="x" in str_mirror,
                y="y" in str_mirror,
                z="z" in str_mirror
            )

    def __init__(
            self, *,
            x_max: Optional[float]=None, y_max: Optional[float]=None, z_max: Optional[float]=None,
            gridstep_mm: Optional[float]=None, pts: Optional[int]=None,
            len_on_x: Optional[int]=None, len_on_y: Optional[int]=None, len_on_z: Optional[int]=None,
            mirror="xyz"
    ):
        """
        3d grid
        :param x_max: maximum length in x direction
        :param y_max: maximum length in y direction
        :param z_max: maximum length in z direction
        :param gridstep_mm: step of the grid
        :param pts: number of points per 'x' direction
        :param len_on_x: the number of points in x direction
        :param len_on_y: the number of points in y direction
        :param len_on_z: the number of points in z direction
        :param mirror: what symmetry the grid has
        Eiter (x_max, y_max, z_max, gridstep_mm) or (len_on_x, len_on_y, len_on_z, [gridstep_mm]) must be defined
        """
        assert (x_max and y_max and z_max and (gridstep_mm or pts)) or (len_on_x and len_on_y and len_on_z), "you must define at list one set of parameters"
        if x_max is not None:
            set_by_physical = True
        else:
            set_by_physical = False

        # the point of the following code part is to define both physical borders and borders in the term of point numbers per dim
        self.x_max = x_max
        self.y_max = y_max
        self.z_max = z_max
        if pts and not gridstep_mm:
            # задано число точек, а не шаг
            if self.x_max:
                gridstep_mm = self.x_max / pts
            else:
                gridstep_mm = 1
        self.gridstep_mm = gridstep_mm
        self.raw_mirror = mirror
        self.mirror = self.MirrorDirection.create_from_str(mirror)
        if set_by_physical:
            self.len_on_x = int(x_max / gridstep_mm)
            self.len_on_y = int(y_max / gridstep_mm)
            self.len_on_z = int(z_max / gridstep_mm)
        else:
            if not gridstep_mm:  # the grid may be defined without physical measure
                self.gridstep_mm = gridstep_mm = 1
            self.x_max = len_on_x * self.gridstep_mm
            self.y_max = len_on_y * self.gridstep_mm
            self.z_max = len_on_z * self.gridstep_mm
            self.len_on_x = len_on_x
            self.len_on_y = len_on_y
            self.len_on_z = len_on_z

        # тут надо для "без отражения" изменить что-нибудь... В зависимости от того, располагаем ли центр по центру или сбоку и всё в этом духе
        self.xs = np.linspace(0, self.x_max, self.len_on_x) if self.mirror.x else np.linspace(-self.x_max/2, self.x_max/2, self.len_on_x)
        self.ys = np.linspace(0, self.y_max, self.len_on_y) if self.mirror.y else np.linspace(-self.y_max/2, self.y_max/2, self.len_on_y)
        self.zs = np.linspace(0, self.z_max, self.len_on_z) if self.mirror.z else np.linspace(-self.z_max/2, self.z_max/2, self.len_on_z)

    def __str__(self):
        return f"grid 3d with len on (x,y,z): ({self.len_on_x}, {self.len_on_y}, {self.len_on_y}), mirror: {self.mirror}"

    def __repr__(self):
        return f"Grid3DParams(len_x={self.len_on_x}, len_y={self.len_on_y}, len_z={self.len_on_z}, gridstepmm={self.gridstep_mm}, mirror={self.mirror})"

    def get_index_float(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        функция определяет индексы на сетке по физической тройки координат.
        Однако, хоть вообще говорят индексы должны быть целочисленные, иногда (например для усреднения) лучше иметь их без округления
        """
        return x / self.gridstep_mm, y / self.gridstep_mm, z / self.gridstep_mm
