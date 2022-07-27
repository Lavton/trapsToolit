"""работа с екзашником симайна"""
import logging
import subprocess
from typing import NoReturn, Dict

from .pa_service import add_raw_extension, add_refined_extension

_NO_GUI_ = "--nogui"  # без GUI
_CONVERGENCE_ = "--convergence"  # точность рефайна
_REFINE_ = "refine"  # процедура рефайна
_FAST_ADJUST_ = "fastadj"  # процедура фаст-аджаста


def refine(simionexe_location: str, filename: str, convergence=1e-3) -> NoReturn:
    """рефайнит сырую ловушку"""
    full_filename = add_raw_extension(filename)
    # "--nogui" for silent moe
    subprocess.run([
        simionexe_location,
        _NO_GUI_,
        _REFINE_,
        f"{_CONVERGENCE_}={convergence}", full_filename
    ])


def fast_adjust(simionexe_location: str, filename: str, voltages: Dict[int, float]) -> NoReturn:
    """
    делает fast adjust
    :param simionexe_location: путь к simion.exe
    :param filename: имя pa файла
    :param voltages: словарь [int->float] - соответствия типу электрода напряжения на нём
    """
    full_filename = add_refined_extension(filename)
    voltage_line = ",".join((
        f"{key}={value}" for key, value in voltages.items()
    ))
    logging.info(f"go to adjust with voltages {voltage_line}")
    subprocess.run([
        simionexe_location,
        _NO_GUI_,
        _FAST_ADJUST_,
        full_filename,
        voltage_line
    ])

