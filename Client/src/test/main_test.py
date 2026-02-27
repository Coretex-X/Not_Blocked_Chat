import flet as ft
import datetime

def main(page: ft.Page):
    page.title = "WhatsApp-like Chat"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    
    #1 - Основные переменные состояния
    messages_column = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    message_input = ft.TextField(
        hint_text="Введите сообщение...",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=3,
    )
    
    #2 - Функция создания сообщения
    def create_chat_message(message: str, is_user: bool = True):
        avatar = ft.CircleAvatar(
            content=ft.Text("ТЫ" if is_user else "ДР"),
            bgcolor=ft.Colors.BLUE if is_user else ft.Colors.GREEN,
        )
        
        message_bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Text(message, color=ft.Colors.WHITE),
                    ft.Text(
                        datetime.datetime.now().strftime("%H:%M"),
                        size=12,
                        color=ft.Colors.WHITE54,
                    ),
                ],
                tight=True,
                spacing=2,
            ),
            bgcolor=ft.Colors.BLUE if is_user else ft.Colors.GREY,
            padding=10,
            border_radius=15,
            margin=ft.margin.only(right=10) if is_user else ft.margin.only(left=10),
        )
        
        if is_user:
            return ft.Row(
                [
                    ft.Container(expand=True),
                    message_bubble,
                    avatar,
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        else:
            return ft.Row(
                [
                    avatar,
                    message_bubble,
                    ft.Container(expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

    #3 - Функция отправки голосового сообщения
    def send_voice_message(message):
        messages_column.controls.append(
            create_chat_message(message=message, is_user=True)
        )
        messages_column.scroll_to(offset=-1, duration=300)
        page.update()
    
    #4 - Функция добавления эмодзи в поле ввода
    def add_emoji_to_input(emoji):
        message_input.value = message_input.value + emoji
        message_input.update()
    
    #5 - Функция переключения видимости панели эмодзи
    def toggle_emoji_picker(e):
        emoji_picker.visible = not emoji_picker.visible
        voice_recorder.visible = False
        emoji_picker.update()
        voice_recorder.update()
    
    #6 - Функция переключения видимости панели записи голоса
    def toggle_voice_recorder(e):
        voice_recorder.visible = not voice_recorder.visible
        emoji_picker.visible = False
        voice_recorder.update()
        emoji_picker.update()
    
    #7 - Основная функция отправки сообщения
    def send_message(e):
        if message_input.value.strip():
            messages_column.controls.append(
                create_chat_message(message=message_input.value, is_user=True)
            )
            message_input.value = ""
            message_input.update()
            messages_column.scroll_to(offset=-1, duration=300)
            page.update()

    #8 - Функция возврата назад
    def go_back(e):
        print("Нажата кнопка назад")
        # Здесь будет логика возврата на предыдущую страницу

    #9 - Функция показа профиля пользователя
    def show_user_profile(e):
        print("Открыт профиль пользователя")
        # Здесь будет логика открытия профиля

    #10 - Создание панели выбора эмодзи
    def create_emoji_picker():
        emoji_container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Выберите эмодзи", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.TextButton("😊", on_click=lambda e: select_emoji("😊")),
                            ft.TextButton("😂", on_click=lambda e: select_emoji("😂")),
                            ft.TextButton("😍", on_click=lambda e: select_emoji("😍")),
                            ft.TextButton("👍", on_click=lambda e: select_emoji("👍")),
                            ft.TextButton("❤️", on_click=lambda e: select_emoji("❤️")),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.TextButton("😎", on_click=lambda e: select_emoji("😎")),
                            ft.TextButton("🙏", on_click=lambda e: select_emoji("🙏")),
                            ft.TextButton("🔥", on_click=lambda e: select_emoji("🔥")),
                            ft.TextButton("🎉", on_click=lambda e: select_emoji("🎉")),
                            ft.TextButton("💯", on_click=lambda e: select_emoji("💯")),
                        ]
                    ),
                ],
                tight=True,
            ),
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.BLACK54,
                offset=ft.Offset(0, 0),
            ),
            padding=10,
            visible=False,
        )
        
        #11 - Вложенная функция выбора эмодзи
        def select_emoji(emoji):
            add_emoji_to_input(emoji)
            emoji_container.visible = False
            emoji_container.update()
        
        return emoji_container

    #12 - Создание панели записи голосового сообщения
    def create_voice_recorder():
        voice_container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Запись голосового сообщения", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.MIC, color=ft.Colors.RED, size=30),
                            ft.Text("Запись... 0:00", size=14),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.TextButton("Отмена", on_click=lambda e: cancel_recording()),
                            ft.TextButton("Отправить", on_click=lambda e: send_recording()),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            padding=20,
            visible=False,
        )
        
        #13 - Функция отмены записи
        def cancel_recording():
            voice_container.visible = False
            voice_container.update()
        
        #14 - Функция отправки голосового сообщения
        def send_recording():
            send_voice_message("Голосовое сообщение")
            voice_container.visible = False
            voice_container.update()
        
        return voice_container

    #15 - Создание компонентов интерфейса
    emoji_picker = create_emoji_picker()
    voice_recorder = create_voice_recorder()

    #16 - Создание верхней панели чата
    chat_header = ft.Container(
        content=ft.Row(
            [
                # Кнопка назад
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=go_back,
                    icon_color=ft.Colors.BLUE,
                ),
                # Кликабельная зона с информацией о пользователе
                ft.GestureDetector(
                    content=ft.Row(
                        [
                            ft.CircleAvatar(
                                content=ft.Text("ДР"),
                                bgcolor=ft.Colors.GREEN,
                            ),
                            ft.Column(
                                [
                                    ft.Text("Друг", weight=ft.FontWeight.BOLD, size=16),
                                    ft.Text("был(а) в сети 5 минут назад", size=12, color=ft.Colors.GREY),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    on_tap=show_user_profile,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=15,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_300)),
    )

    #17 - Создание панели ввода сообщения
    input_row = ft.Container(
        content=ft.Row(
            [
                # Кнопка микрофона
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_VOICE,
                    on_click=toggle_voice_recorder,
                    icon_color=ft.Colors.BLUE,
                ),
                # Поле ввода текста
                message_input,
                # Кнопка эмодзи
                ft.IconButton(
                    icon=ft.Icons.EMOJI_EMOTIONS,
                    on_click=toggle_emoji_picker,
                    icon_color=ft.Colors.BLUE,
                ),
                # Кнопка отправки
                ft.IconButton(
                    icon=ft.Icons.SEND,
                    on_click=send_message,
                    icon_color=ft.Colors.BLUE,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
        padding=10,
        bgcolor=ft.Colors.WHITE,
    )

    #18 - Добавление начальных тестовых сообщений
    messages_column.controls.extend([
        create_chat_message("Привет! Как дела?", is_user=False),
        create_chat_message("Привет! Все отлично, спасибо! А у тебя?", is_user=True),
        create_chat_message("Тоже всё хорошо! Что нового?", is_user=False),
    ])

    #19 - Создание основного контейнера чата
    chat_container = ft.Container(
        content=ft.Column(
            [
                chat_header,
                ft.Container(
                    content=messages_column,
                    expand=True,
                    padding=10,
                    bgcolor=ft.Colors.GREY_100,
                ),
                emoji_picker,
                voice_recorder,
                input_row,
            ],
            expand=True,
        ),
        expand=True,
    )

    #20 - Добавление чата на страницу
    page.add(chat_container)

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8000)


"""
📋 ПОДРОБНОЕ ОПИСАНИЕ КАЖДОГО НОМЕРА:
#1 - Основные переменные состояния

    messages_column: Контейнер для хранения всех сообщений чата с возможностью прокрутки

    message_input: Текстовое поле для ввода новых сообщений с настройками многострочности

#2 - Функция создания сообщения

    Входные данные: текст сообщения и флаг (сообщение от пользователя или от друга)

    Создает: визуальный элемент сообщения с аватаром, текстом и временем

    Возвращает: готовый Row с расположением (слева для друга, справа для пользователя)

#3 - Отправка голосового сообщения

    Принимает: текст сообщения (например, "Голосовое сообщение")

    Добавляет сообщение в историю чата

    Прокручивает чат к последнему сообщению

#4 - Добавление эмодзи в поле ввода

    Принимает: символ эмодзи

    Добавляет эмодзи в конец текста в поле ввода

    Обновляет отображение поля

#5 - Переключение панели эмодзи

    Показывает/скрывает панель выбора эмодзи

    Скрывает панель записи голоса при открытии эмодзи

    Обновляет состояние обоих компонентов

#6 - Переключение панели записи голоса

    Показывает/скрывает панель записи голосового сообщения

    Скрывает панель эмодзи при открытии записи

    Обновляет состояние обоих компонентов

#7 - Основная функция отправки сообщения

    Проверяет: что поле ввода не пустое

    Создает новое сообщение и добавляет в историю

    Очищает поле ввода после отправки

    Прокручивает чат к новому сообщению

#8 - Функция возврата назад

    Обрабатывает нажатие кнопки "Назад"

    В текущей реализации: выводит сообщение в консоль

    Место для интеграции: навигации между экранами

#9 - Функция показа профиля

    Обрабатывает клик по информации о пользователе

    В текущей реализации: выводит сообщение в консоль

    Место для интеграции: открытия профиля пользователя

#10 - Создание панели эмодзи

    Создает контейнер с кнопками эмодзи

    Настраивает внешний вид (тень, скругления, фон)

    Изначально скрыт (visible=False)

#11 - Вложенная функция выбора эмодзи

    Добавляет выбранный эмодзи в поле ввода

    Скрывает панель эмодзи после выбора

    Обновляет отображение

#12 - Создание панели записи голоса

    Создает интерфейс для записи голосовых сообщений

    Отображает состояние записи и кнопки управления

    Изначально скрыт (visible=False)

#13 - Отмена записи голоса

    Скрывает панель записи без отправки сообщения

    Обновляет состояние интерфейса

#14 - Отправка голосового сообщения

    Вызывает функцию отправки с текстом "Голосовое сообщение"

    Скрывает панель записи после отправки

    Обновляет состояние интерфейса

#15 - Создание компонентов интерфейса

    Инициализирует панель эмодзи и панель записи голоса

    Компоненты готовы к использованию в основном интерфейсе

#16 - Создание верхней панели чата

    Содержит: кнопку назад и информацию о пользователе

    Информация о пользователе: кликабельна через GestureDetector

    Отображает: аватар, имя и статус онлайн

#17 - Создание панели ввода

    Содержит: кнопку микрофона, поле ввода, кнопку эмодзи, кнопку отправки

    Настроено вертикальное выравнивание по нижнему краю

    Фон белый для контраста с областью сообщений

#18 - Добавление тестовых сообщений

    Создает начальную историю переписки для демонстрации

    Сообщения от друга и пользователя чередуются

    Показывает различное оформление для разных отправителей

#19 - Создание основного контейнера чата

    Объединяет все компоненты в вертикальную структуру

    Область сообщений имеет серый фон для визуального разделения

    Настроено расширение на всю доступную область

#20 - Добавление чата на страницу

    Размещает готовый контейнер чата на главной странице

    Запускает отображение всего интерфейcа
"""