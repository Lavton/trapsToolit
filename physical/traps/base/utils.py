Dimention = float


class PhysicalBorder:
    """физические "границы" ловушки -- используются в частности для задания границ моделируемой области """
    x: Dimention
    y: Dimention
    z: Dimention

    def __init__(self, x: Dimention, y: Dimention, z: Dimention):
        self.x = x
        self.y = y
        self.z = z