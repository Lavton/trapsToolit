from ....numerical.grid import Grid3DParams
from ....numerical.pa.pa_service import generate_empty_pa, add_raw_extension
from ....physical.traps.base.abstract_trap import AbstractCylCoordinateCell
import numpy as np
from tqdm import tqdm


class NumericalTrapWithCylindicalCoords:
    """
    численное представление для ловушки в цилиндрических координатах
    """
    def __init__(self, trap: AbstractCylCoordinateCell, filename_base: str, pts=200):
        self.trap = trap
        self.filename_base = filename_base
        self.grid = Grid3DParams(x_max=trap.border.x, y_max=trap.border.y, z_max=trap.border.z, pts=pts)

        # поскольку сетка имеет декартову систему координат, в то время как ловушка работает в цилиндрической, нужно всё время осуществлять переход
        # Однако делать это "на месте" долго, поэтому мы кешируем.
        X, Y = np.meshgrid(self.grid.xs, self.grid.ys)
        self._thetas = np.arctan2(Y.T, X.T)
        self._rs = np.sqrt(X.T ** 2 + Y.T ** 2)

    def generate_pa_raw_file(self, for_fast_adjust=True, *, verbose=False):
        """generate file .pa# """
        assert for_fast_adjust
        pa = generate_empty_pa(self.grid)
        filename = add_raw_extension(self.filename_base)
        for k, z in tqdm(enumerate(self.grid.zs), total=self.grid.len_on_z, disable=not verbose):
            for j, y in enumerate(self.grid.ys):
                for i, x in enumerate(self.grid.xs):
                    r, theta = self._rs[i, j], self._thetas[i, j]
                    # r = np.sqrt(y**2+x**2)
                    # theta = np.arctan2(y, x)
                    if self.trap.is_point_is_in_an_electrode(r, theta, z):
                        el_type = self.trap.get_electrode_type_when_electrode(r, theta, z)
                        pa.point(i, j, k, 1, self.trap.electrodeConfiguration.getIndexOfElectrodeType(el_type) + 1)
        pa.save(filename)
