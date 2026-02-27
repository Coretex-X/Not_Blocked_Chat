import flet as ft
import httpx as hx
import sqlite3 as ql
import json as js
import path

db_path = f"{path.db_path()}user_data.db" 
json_path = f"{path.db_path}config/config.jsonc"

def main_sign_up(page: ft.Page):
    page.title = "Авторизацыя"
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
            
        # Подготовка данных
        data = {
            'login': text_input_login.value,
            'password': text_input_password.value
        }

        #try:
            # Отправка на сервер
        async with hx.AsyncClient() as client:
                response = await client.post(
                    'http://127.0.0.1:5000/api/v2/user/login/',
                    json=data
                )
                
        if response.status_code == 200:
                    json_response = response.json()
                    # Извлекаем токены
                    id_user = json_response["id_users"]
                    name = json_response["name"]
                    message = json_response["meaning"]
                    with ql.connect(db_path) as con:
                        cur = con.cursor()
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS users_data(
                            id_user TEXT,                            
                            name TEXT,
                            profile TEXT,
                            PRIMARY KEY (access_token)
                            );
                        """)
                        cur.execute(f"INSERT INTO users_data (access_token, name) VALUES ('{id_user}', '{name}')")

                        data['is_authenticated'] = True

                        with open(json_path, 'w') as f:
                            js.dump(data, f, indent=4)  # indent для красивого форматирования

                        print(message)
                        # Очистка полей после успешной отправки
                        text_input_login.value = ""
                        text_input_password.value = ""
                        #Перенапровляем на главную страницу
                        page.go('/')
                        page.update()
                    cur.close()
        else:
                    error_text.value = f"Error:{response}"
                    error_text.visible = True
                    error_text.update()
                    
        #except Exception as ex:
         #   error_text.value = f"Ошибка соединения: {str(ex)}"
         #   error_text.visible = True
          #  error_text.update()

    # Элементы интерфейса
    label = ft.Text('Авторизация:', size=30)
    
    text_input_login = ft.TextField(
        label='Имя пользователя',
        autofocus=True
    )
    
    text_input_password = ft.TextField(
        label='Пароль',
        password=True,
        can_reveal_password=True
    )
      
    button = ft.ElevatedButton(
        'Войти',
        on_click=rest_api
    )
    
    or_redistration = ft.Text('Нет аккаунта?')

    button_registration = ft.ElevatedButton(
        'Зарегистрироватся',
        on_click= lambda _: page.go('/registration')
    )

    # Добавляем поля в список обязательных
    required_fields = [
        text_input_login,
        text_input_password
    ]

    # Собираем интерфейс
    return ft.View(
    "/login",
    [
        ft.Container(
            ft.Column(
                [
                    ft.Container(label, margin=5),
                    ft.Container(text_input_login, margin=5),
                    ft.Container(text_input_password, margin=5),
                    ft.Container(error_text, margin=5),
                    ft.Container(button, margin=5, alignment=ft.alignment.center),
                    ft.Container(or_redistration, margin=5, alignment=ft.alignment.center),
                    ft.Container(button_registration, margin=5, alignment=ft.alignment.center)
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
