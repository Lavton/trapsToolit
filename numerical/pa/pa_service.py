from ...SIMION.PA import PA
from ...numerical.grid import Grid3DParams


def generate_empty_pa(grid: Grid3DParams, fast_adjustable=0) -> PA:
    """создаёт пустой PA файл"""
    return PA(
        symmetry='planar',  # symmetry type: 'planar' or 'cylindrical'
        max_voltage=100000,  # this affects the interpretation
        #   of point values
        nx=grid.len_on_x,  # x dimension in grid units
        ny=grid.len_on_y,  # y dimension in grid units
        nz=grid.len_on_z,  # z dimension in grid units
        mirror=grid.raw_mirror,  # mirroring (subset of "xyz")
        field_type='electrostatic',  # field type: 'electrostatic' or 'magnetic'
        ng=100,  # ng scaling factor for magnetic arrays.
        # The following three fields are only supported in SIMION 8.1
        dx_mm=grid.gridstep_mm,  # grid unit size (mm) in X direction
        dy_mm=grid.gridstep_mm,  # grid unit size (mm) in Y direction
        dz_mm=grid.gridstep_mm,  # grid unit size (mm) in Z direction
        fast_adjustable=fast_adjustable,  # Boolean indicating whether is fast-adj.
        enable_points=1  # Enable data points.
    )


def get_grid_from_pa(pa: PA) -> Grid3DParams:
    return Grid3DParams(
        len_on_x=pa.nx(),
        len_on_y=pa.ny(),
        len_on_z=pa.nz(),
        gridstep_mm=pa.dx_mm(),
        mirror=pa.mirror()
    )

_PA_RAW_EXTENSION = ".pa#"  # начальная расширение
_PA_REFINED_EXTENSION = ".pa0"  # рефайнутое расширение


def add_raw_extension(filename: str) -> str:
    """добавить расширение сырой ловшуки"""
    if filename.endswith(_PA_RAW_EXTENSION):
        return filename
    else:
        return filename + _PA_RAW_EXTENSION


def add_refined_extension(filename: str) -> str:
    """добавить расширение рефайнутой ловушки"""
    if filename.endswith(_PA_REFINED_EXTENSION):
        return filename
    else:
        return filename + _PA_REFINED_EXTENSION
