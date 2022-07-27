from ....physical.electodes.base.electrode_conf import ElectrodeConfiguration, Volts
from typing import Dict


def voltage_config_to_adjust_dict(electrode_configuration: ElectrodeConfiguration) -> Dict[int, Volts]:
    """
    Преобразует имеющующиеся электроды под напряжением в словарь (номер электрода - напряжение). Этот словарь подаётся в fast_adjust
    """
    return {(i+1): e.voltage for i, e in enumerate(electrode_configuration.electrodes)}
