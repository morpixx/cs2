### 1. Финальный Технологический Стек

Мы берем лучшее для каждой задачи, чтобы обеспечить скорость (FPS) и скрытность.

* **Язык:** Python 3.10+ (64-bit).
* **Память (Core):** `Pymem` — чтение структур, сканирование сигнатур.
* **Глаза (Vision):** `DXCam` (захват экрана 144+ FPS) + `Ultralytics YOLOv8` (TensorRT engine для скорости).
* **Математика:** `NumPy` (векторная алгебра) + `FilterPy` (фильтры Калмана для предикшна и сглаживания).
* **Визуал (ESP/UI):** `pyMeow` (для рисования оверлея и ESP — это быстрее, чем DPG) + `Dear PyGui` (для красивого меню настроек, которое можно скрывать/показывать).
* **Ввод (Input):** `Logitech G-Hub DLL` (через `ctypes`) — эмуляция драйвера мыши.

---

### 2. Структура Проекта (File Tree)

Не вали всё в один файл. Модульность спасет тебе нервы при отладке.

```text
NeuroApex/
│
├── main.py                 # Точка входа. Запуск потоков (UI, Logic, Overlay).
├── config.json             # Файл с настройками (сохраняется из меню).
├── ghub_device.dll         # Драйвер Logitech.
│
├── core/                   # Низкоуровневая база
│   ├── memory.py           # Класс GameProcess (Pymem). Чтение/Запись.
│   ├── signatures.py       # Словарь твоих паттернов (b"\xAA\xBB...").
│   ├── offset_manager.py   # Сканер. Превращает сигнатуры в адреса (Offsets).
│   └── input_handler.py    # Обертка над ghub_device.dll (Move, Click).
│
├── game/                   # Данные игры (CS2 specific)
│   ├── entity.py           # Класс Player (HP, Team, Pos, WeaponID, BoneMatrix).
│   ├── weapons.py          # База данных оружия (RCS паттерны, скорострельность).
│   └── math_utils.py       # WorldToScreen, CalcAngle, GetDistance.
│
├── ai/                     # Модуль нейросети
│   ├── detector.py         # Запуск YOLOv8, обработка кадра DXCam.
│   └── models/             # Папка с файлом best.pt (обученная модель).
│
├── features/               # Реализация читов
│   ├── esp.py              # Рисование (Box, Skeleton, Radar, Warnings).
│   ├── aimbot.py           # Логика наводки (Hybrid: Memory + AI).
│   ├── rcs.py              # Контроль отдачи (Recoil Control).
│   └── triggerbot.py       # Авто-выстрел.
│
└── ui/                     # Интерфейс
    ├── overlay.py          # Отрисовка ESP через pyMeow.
    └── menu.py             # Меню настроек через Dear PyGui.
```

---

### 3. Детальный разбор функций и реализации

#### А. Чтение памяти и Авто-обновление

* **Как работает:** При старте `offset_manager.py` сканирует `client.dll` на наличие сигнатур (LocalPlayer, EntityList, ViewMatrix).
* **Реализация:** Используй `pymem.pattern_scan_module`. Результаты сохраняй в глобальный словарь `Offsets`. Если игра обновилась, но код остался похожим, чит сам найдет новые адреса.

#### Б. Продвинутый ESP (Visuals)

Все рисуем через `pyMeow` поверх прозрачного окна.

1. **Скелеты/Боксы:** Читаем `BoneMatrix` из памяти. Если `Team == MyTeam` — рисуем скелет (зеленый), бокс не рисуем. Если враг — красный бокс + скелет.
2. **Info Bar:** Текст рядом с боксом: `[Weapon Name] | [HP] | [Armor Icon]`.
    * *Бомба:* Проверяем переменную `m_bHasC4` у игрока. Если `True` -> Рисуем значок бомбы над головой.
3. **Back-Track Alert (Спина):**
    * Считаем угол между "куда смотрю я" и "где враг".
    * Если враг сзади (угол > 90) и дистанция < 15м -> Рисуем красную дугу или текст "ENEMY BEHIND" в центре экрана.
4. **2D Радар:**
    * Рисуем круг в углу экрана.
    * Центр круга = Ты.
    * Враги проецируются на круг: `RadarX = (EnemyX - MyX) * Scale`. Нужно учитывать поворот игрока (вращать точки на радаре по формуле поворота вектора).

#### В. Гибридный Аимбот (Aimbot) + AI

Это самая сложная часть. Алгоритм действий:

1. **Поиск целей (Memory):** Сначала получаем список всех живых врагов из памяти. Сортируем их по `CrosshairDistance` (кто ближе к прицелу).
2. **Проверка видимости (Hybrid):**
    * *Memory check:* Проверяем флаг `m_bSpottedByMask` (видит ли сервер игрока). Это быстро, но не всегда точно.
    * *AI check:* Делаем скриншот центра экрана (DXCam). YOLO ищет головы. Если бокс YOLO совпадает с примерным положением врага из памяти — значит, он точно видим.
3. **Выбор кости (Bone Priority):**
    * Если `Visible(Head)` -> Целимся в голову.
    * Иначе если `Visible(Neck)` -> Шея.
    * Иначе -> Тело (Stomach).
4. **Предикшн (Prediction):**
    * Берем `Velocity` (вектор скорости) врага из памяти.
    * `AimPoint = BonePos + (Velocity * (Distance / BulletSpeed))`.
5. **Фильтр (Humanization):**
    * Передаем идеальную точку `AimPoint` в Фильтр Калмана. Он выдает "сглаженную" координату.
    * G-Hub драйвер двигает мышь.

#### Г. Ван-тапы и Триггербот

* **One-Tap Mode:**
  * Включает триггербот с задержкой 0 мс.
  * Аимбот наводится *только* на голову.
  * Как только прицел на голове (проверка по углу или через YOLO) -> `ghub.click()`.
  * После выстрела аимбот отключается на 0.5 сек (reset), чтобы не спреить.

#### Д. Контроль отдачи (RCS - Recoil Control System)

В CS2 отдача хранится в `m_aimPunchAngle`.

* **Логика:** Чит читает, куда "улетает" прицел (Punch Angle).
* **Действие:** Двигаем мышь в *противоположную* сторону.
* **Формула:** `TargetAngle = ViewAngle - (AimPunchAngle * 2.0)`.
* **База оружия:** В `weapons.py` делаем словарь:

    ```python
    WEAPONS = {
        7: "AK-47",   # ID калаша
        1: "Deagle",  # RCS не нужен
        # ...
    }
    ```

    Если у тебя в руках AK-47 -> Включаем RCS. Если пистолет -> Выключаем.

---

### 4. Дополнительные функции (Suggestions)

Что добавить, чтобы софт был "Топ уровня":

1. **Spectator List (Важно!):**
    * Читаем из памяти, кто сейчас наблюдает за твоим игроком.
    * Если за тобой кто-то смотрит — автоматически рисуем предупреждение "SPECTATOR WARNING". Это спасает от банов.
2. **Flash Check:**
    * Читаем `m_flFlashDuration`.
    * Если значение > 0 (ты ослеплен) -> Отключаем Аимбот, чтобы не спалиться стрельбой вслепую.
3. **Sound ESP (Sonar):**
    * Чем ближе враг, тем чаще пищит звук (как парктроник). Полезно при клатчах 1vs1.
4. **Auto Pistol:**
    * Если в руках пистолет, зажимаешь ЛКМ -> чит кликает быстро сам.

---

### 5. Флоу работы (Workflow)

Вот как это работает в коде (`main.py`):

```python
def game_loop():
    # 1. Скан паттернов (1 раз при запуске)
    scanner.update_offsets() 
    
    while True:
        # 2. Обновление настроек из меню
        config = menu.get_config()
        
        # 3. Чтение данных (Memory)
        # Читаем сразу весь массив игроков для производительности
        local_player = memory.get_local_player()
        enemies = memory.get_enemies()
        view_matrix = memory.get_view_matrix()
        
        # 4. Обработка ИИ (Vision) - запускаем раз в 3-4 кадра (оптимизация)
        if frame_count % 3 == 0:
            ai_boxes = detector.scan_screen()
            
        # 5. ESP (Visuals)
        overlay.start_frame()
        for enemy in enemies:
            # Математика W2S
            coords = math.world_to_screen(enemy.pos, view_matrix)
            
            # Логика отрисовки
            if config['esp_box']: 
                esp.draw_box(coords, enemy.health)
            if config['esp_skeleton']:
                esp.draw_skeleton(enemy.bone_matrix, view_matrix)
                
            # Радар и предупреждения
            if config['radar']:
                esp.draw_on_radar(local_player, enemy)
                
        overlay.end_frame()
        
        # 6. Логика Аима и RCS (Aim Logic)
        # Если нажата кнопка аима (проверка win32api.GetAsyncKeyState)
        if input_handler.is_key_down(config['aim_key']):
            
            # Поиск цели
            target = aimbot.get_best_target(enemies, local_player, ai_boxes)
            
            if target:
                # Предикшн + Калман
                aim_point = aimbot.predict(target, local_player)
                
                # RCS (если стреляем)
                if local_player.shots_fired > 1:
                    aim_point = rcs.apply_recoil(aim_point, local_player.aim_punch)
                
                # Движение мыши через G-Hub
                ghub.move_to(aim_point)
                
                # Авто-выстрел (Triggerbot)
                if config['triggerbot'] and aimbot.is_looking_at(target):
                    ghub.click()
```

### С чего начать прямо сейчас?

1. **Настрой G-Hub:** Найди `ghub_device.dll` и напиши скрипт, который просто двигает курсор кругом. Проверь в Paint.
2. **Память:** Сделай скрипт, который выводит в консоль Здоровье твоего игрока в реальном времени.
3. **Визуал:** Подключи `pyMeow` и нарисуй просто квадрат вокруг своего прицела.

Как только эти 3 компонента заработают по отдельности — начинай собирать их в структуру выше.
