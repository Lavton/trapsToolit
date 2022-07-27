from enum import Enum, auto
from typing import Dict, Optional, List

Volts = float  # type-alias


class ElectrodeType:
    """
    тип электрода. Электроды одного типа имеют одно напряжение всегда. Приватный конструктор, не используйте его!
    """
    voltage: Optional[Volts] = None  # на электрод может быть подано напряжение


class ElectrodeConfiguration:
    electrodes: List[ElectrodeType]

    def __init__(self):
        self.electrodes = []

    def addAnotherElectrode(self) -> ElectrodeType:
        """
        добавляет новый электрод
        """
        self.electrodes.append(ElectrodeType())
        return self.electrodes[-1]

    def getIndexOfElectrodeType(self, electrode_type: ElectrodeType) -> int:
        """
        находит индекс заданного электрода
        """
        for i, electrode in enumerate(self.electrodes):
            if electrode_type is electrode:
                return i
        assert False
