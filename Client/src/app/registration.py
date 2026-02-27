import flet as ft
import httpx as hx
import json as js


def main_registartion(page: ft.Page):
    page.title = "Регистрация"
    #page.theme_mode = data["theme"]
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Переменные для валидации
    required_fields = []
    error_text = ft.Text(color="red", visible=False)

    def validate_fields():
        # Проверяем все обязательные поля
        for field in required_fields:
            if not field.value:
                field.error_text = "Это поле обязательно для заполнения"
                field.update()
                return False
            
        return True

    def validate_password():
        if text_input_password.value != text_input_password_clon.value:
            text_input_password.error_text = "Пароли не совпадают"
            text_input_password_clon.error_text = "Пароли не совпадают"
            text_input_password.update()
            text_input_password_clon.update()
            return False
        return True

    async def rest_api(e):
        # Сбрасываем ошибки
        error_text.visible = False
        error_text.update()
        
        for field in required_fields:
            field.error_text = None
            field.update()

        # Валидация
        if not validate_fields():
            return
            
        if not validate_password():
            return

        # Подготовка данных
        data = {
            'login': text_input_login.value,
            'email': text_input_email.value,
            'number':text_input_number,
            'password': text_input_password.value
        }

        try:
            # Отправка на сервер
            async with hx.AsyncClient() as client:
                response = await client.post(
                    'http://127.0.0.1:5000/api/v2/user/registration/',
                    json=data
                )
                
                if response.status_code == 200:
                    # Очистка полей после успешной отправки
                    text_input_login.value = ""
                    text_input_email.value = ""
                    text_input_password.value = ""
                    text_input_password_clon.value = ""
                    page.go('/login')
                    page.update()
                else:
                    error_text.value = f"Ошибка сервера: {response.text}"
                    error_text.visible = True
                    error_text.update()
                    
        except Exception as ex:
            error_text.value = f"Ошибка соединения: {str(ex)}"
            error_text.visible = True
            error_text.update()

    # Элементы интерфейса
    label = ft.Text('Регистрация:', size=30)
    
    text_input_login = ft.TextField(
        label='Имя пользователя',
        autofocus=True
    )
    
    text_input_email = ft.TextField(
        label='E-Mail'
    )

    text_input_number = ft.TextField(
        label='Телефон')
    
    text_input_password = ft.TextField(
        label='Пароль',
        password=True,
        can_reveal_password=True
    )
    
    text_input_password_clon = ft.TextField(
        label='Повторите пароль',
        password=True,
        can_reveal_password=True
    )
    
    button = ft.ElevatedButton(
        'Зарегистрироваться',
        on_click=rest_api
    )

    or_sign_up = ft.Text('Есть аккаунт?')

    button_sign_up = ft.ElevatedButton(
        'Войти',
        on_click= lambda _: page.go('/login')
    )

    # Добавляем поля в список обязательных
    required_fields = [
        text_input_login,
        text_input_email,
        text_input_number,
        text_input_password,
        text_input_password_clon
    ]

    # Собираем интерфейс
    return ft.View(
        "/registration",
        [
            ft.Container(
                ft.Column(
                    [
                        ft.Container(label, margin=5),
                        ft.Container(text_input_login, margin=5),
                        ft.Container(text_input_email, margin=5),
                        ft.Container(text_input_number, margin=5),
                        ft.Container(text_input_password, margin=5),
                        ft.Container(text_input_password_clon, margin=5),
                        ft.Container(error_text, margin=5),
                        ft.Container(button, margin=5, alignment=ft.alignment.center),
                        ft.Container(or_sign_up, margin=5, alignment=ft.alignment.center),
                        ft.Container(button_sign_up, margin=5, alignment=ft.alignment.center)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    width=400
                ),
                expand=True,  # Растягиваем на весь доступный размер
                alignment=ft.alignment.center  # Центрируем содержимое
            )
        ],
        # appbar=appbar,  # раскомментируйте если нужно
        # navigation_bar=navigation_bar  # раскомментируйте если нужно
    )

