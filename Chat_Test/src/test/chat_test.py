import flet as ft
import datetime

def main(page: ft.Page):
    page.title = "WhatsApp-like Chat"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    
    # Переменные состояния
    messages_column = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    message_input = ft.TextField(
        hint_text="Введите сообщение...",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=3,
    )
    
    # Функция для создания сообщения
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

    # Функции для работы с сообщениями
    def send_voice_message(message):
        messages_column.controls.append(
            create_chat_message(message=message, is_user=True)
        )
        messages_column.scroll_to(offset=-1, duration=300)
        page.update()
    
    def add_emoji_to_input(emoji):
        message_input.value = message_input.value + emoji
        message_input.update()
    
    def toggle_emoji_picker(e):
        emoji_picker.visible = not emoji_picker.visible
        voice_recorder.visible = False
        emoji_picker.update()
        voice_recorder.update()
    
    def toggle_voice_recorder(e):
        voice_recorder.visible = not voice_recorder.visible
        emoji_picker.visible = False
        voice_recorder.update()
        emoji_picker.update()
    
    def send_message(e):
        if message_input.value.strip():
            messages_column.controls.append(
                create_chat_message(message=message_input.value, is_user=True)
            )
            message_input.value = ""
            message_input.update()
            messages_column.scroll_to(offset=-1, duration=300)
            page.update()

    def go_back(e):
        print("Нажата кнопка назад")
        # Здесь можно добавить логику возврата на предыдущую страницу

    def show_user_profile(e):
        print("Открыт профиль пользователя")
        # Здесь можно добавить логику открытия профиля

    # Создаем панель эмодзи
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
        
        def select_emoji(emoji):
            add_emoji_to_input(emoji)
            emoji_container.visible = False
            emoji_container.update()
        
        return emoji_container

    # Создаем панель записи голоса
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
        
        def cancel_recording():
            voice_container.visible = False
            voice_container.update()
        
        def send_recording():
            send_voice_message("Голосовое сообщение")
            voice_container.visible = False
            voice_container.update()
        
        return voice_container

    # Создаем компоненты
    emoji_picker = create_emoji_picker()
    voice_recorder = create_voice_recorder()

    # Верхняя панель чата с кнопкой назад и кликабельной зоной
    chat_header = ft.Container(
        content=ft.Row(
            [
                # Кнопка назад
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=go_back,
                    icon_color=ft.Colors.BLUE,
                ),
                # Кликабельная зона с аватаром и информацией
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

    # Панель ввода сообщения
    input_row = ft.Container(
        content=ft.Row(
            [
                # Кнопка микрофона
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_VOICE,
                    on_click=toggle_voice_recorder,
                    icon_color=ft.Colors.BLUE,
                ),
                # Поле ввода
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

    # Добавляем начальные сообщения
    messages_column.controls.extend([
        create_chat_message("Привет! Как дела?", is_user=False),
        create_chat_message("Привет! Все отлично, спасибо! А у тебя?", is_user=True),
        create_chat_message("Тоже всё хорошо! Что нового?", is_user=False),
    ])

    # Основной контейнер чата
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

    # Добавляем чат на страницу
    page.add(chat_container)

if __name__ == "__main__":
    ft.app(target=main)