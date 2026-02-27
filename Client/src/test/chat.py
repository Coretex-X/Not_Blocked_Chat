import flet as ft
from datetime import datetime

def main(page: ft.Page):
    # Настройки страницы
    page.title = "Мой Мессенджер"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.fonts = {
        "Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
    }
    page.theme = ft.Theme(font_family="Roboto")
    
    # Контакты (пример данных)
    contacts = [
        {"name": "Алексей Петров", "last_msg": "Привет, как дела?", "time": "10:30", "unread": 2},
        {"name": "Мария Иванова", "last_msg": "Договорились на завтра", "time": "09:15", "unread": 0},
        {"name": "Иван Сидоров", "last_msg": "Отправил документы", "time": "Вчера", "unread": 5},
        {"name": "Ольга Васильева", "last_msg": "Спасибо за помощь!", "time": "Вчера", "unread": 0},
        {"name": "Дмитрий Алексеев", "last_msg": "Когда встретимся?", "time": "Пн", "unread": 1},
    ]
    
    # Сообщения в чате (пример данных)
    chat_messages = [
        {"sender": "Алексей Петров", "text": "Привет!", "time": "10:20", "is_me": False},
        {"sender": "Я", "text": "Привет! Как дела?", "time": "10:22", "is_me": True},
        {"sender": "Алексей Петров", "text": "Все отлично, спасибо! А у тебя?", "time": "10:25", "is_me": False},
        {"sender": "Я", "text": "Тоже всё хорошо. Что насчёт встречи?", "time": "10:28", "is_me": True},
        {"sender": "Алексей Петров", "text": "Давай в пятницу в 18:00?", "time": "10:30", "is_me": False},
    ]
    
    # Создаем список контактов
    def create_contact(contact):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.CircleAvatar(
                        content=ft.Text(contact["name"][0]),
                        radius=25
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(contact["name"], weight=ft.FontWeight.BOLD),
                            ft.Text(contact["last_msg"], size=12, color=ft.Colors.GREY_600),
                        ],
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                        expand=True
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(contact["time"], size=12, color=ft.Colors.GREY_600),
                            ft.Container(
                                content=ft.Text(str(contact["unread"])), 
                                bgcolor=ft.Colors.GREEN if contact["unread"] > 0 else None,
                                width=20,
                                height=20,
                                border_radius=10,
                                alignment=ft.alignment.center
                            ) if contact["unread"] > 0 else ft.Container(width=20, height=20)
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.END
                    )
                ],
                spacing=10
            ),
            padding=10,
            on_click=lambda e: open_chat(contact),
            border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_300)),
        )
    
    # Создаем сообщение в чате
    def create_message(message):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(message["sender"], weight=ft.FontWeight.BOLD, size=12) if not message["is_me"] else None,
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(message["text"]),
                                ft.Text(message["time"], size=10, color=ft.Colors.GREY_600, text_align=ft.TextAlign.END),
                            ],
                            spacing=2,
                            tight=True
                        ),
                        bgcolor=ft.Colors.BLUE_100 if message["is_me"] else ft.Colors.GREY_200,
                        padding=10,
                        border_radius=10,
                        alignment=ft.alignment.center_left if not message["is_me"] else ft.alignment.center_right
                    )
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.END if message["is_me"] else ft.CrossAxisAlignment.START
            ),
            padding=5,
            margin=ft.margin.only(bottom=5)
        )
    
    # Функция открытия чата
    def open_chat(contact):
        chat_header.content = ft.Text(contact["name"], size=20, weight=ft.FontWeight.BOLD)
        chat_messages_column.controls = [create_message(msg) for msg in chat_messages]
        page.update()
    
    # Элементы интерфейса
    # Заголовок списка контактов
    contacts_header = ft.Container(
        content=ft.Text("Чаты", size=20, weight=ft.FontWeight.BOLD),
        padding=15,
        alignment=ft.alignment.center_left,
        bgcolor=ft.Colors.GREY_200
    )
    
    # Список контактов
    contacts_column = ft.Column(
        controls=[create_contact(contact) for contact in contacts],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True
    )
    
    # Заголовок чата
    chat_header = ft.Container(
            content=ft.Text("Выберите чат", size=20, weight=ft.FontWeight.BOLD),
            padding=15,
            bgcolor=ft.Colors.GREY_200,
            alignment=ft.alignment.center_left
        )
    
    # Сообщения в чате
    chat_messages_column = ft.Column(
        controls=[],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True
    )
    
    # Поле ввода сообщения
    message_input = ft.TextField(
        hint_text="Введите сообщение...",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=5
    )
    
    # Кнопка отправки
    send_button = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color=ft.Colors.BLUE,
        on_click=lambda e: send_message()
    )
    
    # Функция отправки сообщения
    def send_message():
        if message_input.value.strip():
            new_message = {
                "sender": "Я",
                "text": message_input.value,
                "time": datetime.now().strftime("%H:%M"),
                "is_me": True
            }
            chat_messages.append(new_message)
            chat_messages_column.controls.append(create_message(new_message))
            message_input.value = ""
            page.update()
            chat_messages_column.scroll_to(offset=-1, duration=300)
    
    # Собираем интерфейс
    page.add(
        ft.Row(
            controls=[
                # Боковая панель с контактами
                ft.Container(
                    content=ft.Column(
                        controls=[contacts_header, contacts_column],
                        spacing=0,
                        expand=True
                    ),
                    width=350,
                    border=ft.border.only(right=ft.border.BorderSide(1, ft.Colors.GREY_300))
                ),
                # Область чата
                ft.Column(
                    controls=[
                        # Шапка чата
                        ft.Container(
                            content=chat_header,
                            padding=15,
                            bgcolor=ft.Colors.GREY_200,
                            alignment=ft.alignment.center_left
                        ),
                        # Сообщения
                        chat_messages_column,
                        # Панель ввода
                        ft.Container(
                            content=ft.Row(
                                controls=[message_input, send_button],
                                spacing=10,
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            padding=10,
                            bgcolor=ft.Colors.GREY_200
                        )
                    ],
                    expand=True,
                    spacing=0
                )
            ],
            expand=True,
            spacing=0
        )
    )

ft.app(target=main,view=ft.AppView.WEB_BROWSER, port=8000)