import flet as ft
import httpx as hx
import sqlite3 as ql
import path

db_path = f"{path.db_path()}user_data.db"

def main_sign_up(page: ft.Page):
    page.title = "Авторизация"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    error_text = ft.Text(color="red", visible=False)

    def validate_fields():
        for field in [text_input_login, text_input_password]:
            if not field.value:
                field.error_text = "Это поле обязательно"
                field.update()
                return False
        return True

    async def rest_api(e):
        error_text.visible = False
        error_text.update()
        for field in [text_input_login, text_input_password]:
            field.error_text = None
            field.update()

        if not validate_fields():
            return

        try:
            async with hx.AsyncClient() as client:
                response = await client.post(
                    'http://127.0.0.1:5000/api/v2/user/login/',
                    json={'login': text_input_login.value, 'password': text_input_password.value}
                )

            if response.status_code == 200:
                r = response.json()
                with ql.connect(db_path) as con:
                    cur = con.cursor()
                    cur.execute(
                        "INSERT INTO users_data (id_user, name, profile, number, token) VALUES (?, ?, ?, ?, ?)",
                        (r["id_users"], r["login"], r.get("profile", ""), r.get("number", ""), r["token"])
                    )
                    con.commit()
                text_input_login.value = ""
                text_input_password.value = ""
                page.go('/')
                page.update()
            else:
                error_text.value = f"Ошибка: {response.status_code}"
                error_text.visible = True
                error_text.update()
        except Exception as ex:
            error_text.value = f"Ошибка соединения: {str(ex)}"
            error_text.visible = True
            error_text.update()

    label = ft.Text('Авторизация:', size=30)
    text_input_login = ft.TextField(label='Имя пользователя', autofocus=True)
    text_input_password = ft.TextField(label='Пароль', password=True, can_reveal_password=True)
    button = ft.ElevatedButton('Войти', on_click=rest_api)

    return ft.View("/login", [
        ft.Container(
            ft.Column([
                ft.Container(label, margin=5),
                ft.Container(text_input_login, margin=5),
                ft.Container(text_input_password, margin=5),
                ft.Container(error_text, margin=5),
                ft.Container(button, margin=5, alignment=ft.alignment.center),
                ft.Container(ft.Text('Нет аккаунта?'), margin=5, alignment=ft.alignment.center),
                ft.Container(
                    ft.ElevatedButton('Зарегистрироваться', on_click=lambda _: page.go('/registration')),
                    margin=5, alignment=ft.alignment.center
                )
            ], alignment=ft.MainAxisAlignment.CENTER, width=400),
            expand=True, alignment=ft.alignment.center
        )
    ])