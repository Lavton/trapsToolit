# Тулкит для работы с ионными ловушками 
Создана в первую очередь для FT-ICR, но должна быть достаточно гибкой для других ловушек...

## Устройство библиотеки
в пакете `physical` лежат вещи, связанные с физическим устройством ловушек. А именно:
- электроды (классы ElectrodeType) и (ElectrodeConfiguration)
- физическая модель ловушки (CylinderTrap)

В пакете `numerical` лежат вещи, которые призваны создать численную модель физических ловушек.
В частности: 
- `traps` содержит тулзы для генерации .pa файла по физической модели, 
- `grid` моделирует сетку
- `pa_service` служит для создания и работы с .pa файлами
- `exe` подключает simion.exe для refine и fast_adjust