import flet as ft
import sqlite3 as sql
import path
import requests as http

db_path = f"{path.db_path()}user_data.db"

# Отправка изменённых данных пользователя (POST)
PROFILE_UPDATE_URL =     "http://127.0.0.1:5000/search/v2/user/update_user_data/"


# Удаление аккаунта (POST, в теле id и token)
ACCOUNT_DELETE_URL = "http://127.0.0.1:5000/search/v2/user/delete_user/"


# ── БД ───────────────────────────────────────────────────────────────────────

def _migrate_settings():
    """Добавляет font_size если нет."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute("ALTER TABLE user_settings ADD COLUMN font_size TEXT DEFAULT '14'")
        except sql.OperationalError:
            pass
        con.commit()


def _load_settings() -> dict:
    _migrate_settings()
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT color_theme, font_size FROM user_settings LIMIT 1")
            row = cur.fetchone()
            if row:
                return {"color_theme": row[0] or "dark", "font_size": int(row[1] or 14)}
        except sql.OperationalError:
            pass
    return {"color_theme": "dark", "font_size": 14}


def _save_setting(key: str, value: str):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(f"UPDATE user_settings SET {key} = ?", (value,))
        con.commit()


def _load_user() -> dict:
    """Возвращает словарь с данными пользователя, включая id и token."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute(
                "SELECT id_user, name, profile, number, avatar, token FROM users_data LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                return {
                    "id":       row[0],
                    "name":     row[1] or "",
                    "profile":  row[2] or "",
                    "number":   row[3] or "",
                    "avatar":   row[4] or "",
                    "token":    row[5] or "",
                }
        except sql.OperationalError:
            pass
    return {"id": "", "name": "", "profile": "", "number": "", "avatar": "", "token": ""}


def _apply_font(page: ft.Page, size: int):
    t = ft.TextTheme(
        body_medium=ft.TextStyle(size=size),
        body_large=ft.TextStyle(size=size + 2),
        body_small=ft.TextStyle(size=size - 2),
    )
    page.theme      = ft.Theme(text_theme=t)
    page.dark_theme = ft.Theme(text_theme=t)


# ── Вид ──────────────────────────────────────────────────────────────────────

def settings_view(page: ft.Page) -> ft.View:
    settings = _load_settings()
    user     = _load_user()
    is_dark  = settings["color_theme"] == "dark"

    # ─── Цвета для текущей темы ─────────────────────────────────────────────

    def get_colors():
        """Возвращает словарь с цветами для текущей темы."""
        dark = is_dark
        return {
            "title": ft.Colors.ON_SURFACE,
            "subtitle": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700,
            "label": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700,
        }

    colors = get_colors()

    # ─── Функция обновления всех цветов ─────────────────────────────────────

    def update_all_colors():
        """Обновляет цвета всех текстовых элементов при смене темы."""
        c = get_colors()
        
        # Профиль
        name_text.color = c["title"]
        profile_text.color = c["subtitle"]
        
        # Тема оформления
        theme_title.color = c["title"]
        theme_label.color = c["label"]
        theme_icon.color = c["label"]
        theme_icon.name = ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE
        
        # Размер шрифта
        font_title.color = c["title"]
        font_size_lbl.color = c["label"]
        font_icon.color = c["label"]
        font_preview.color = c["label"]
        
        # Опасная зона
        danger_icon.color = ft.Colors.RED
        danger_title.color = ft.Colors.RED
        
        # TextField'ы в диалоге
        f_name.color = c["title"]
        f_name.label_style = ft.TextStyle(color=c["label"])
        f_number.color = c["title"]
        f_number.label_style = ft.TextStyle(color=c["label"])
        f_profile.color = c["title"]
        f_profile.label_style = ft.TextStyle(color=c["label"])
        
        # Заголовок диалога
        edit_dlg.title.color = c["title"]
        
        # AppBar
        appbar.title.color = c["title"]
        
        page.update()

    # ── Диалог редактирования профиля ─────────────────────────────────────

    f_name    = ft.TextField(
        label="Имя",
        value=user["name"],
        border_radius=10,
        color=colors["title"],
        label_style=ft.TextStyle(color=colors["label"]),
    )
    f_number  = ft.TextField(
        label="Номер",
        value=user["number"],
        border_radius=10,
        keyboard_type=ft.KeyboardType.PHONE,
        color=colors["title"],
        label_style=ft.TextStyle(color=colors["label"]),
    )
    f_profile = ft.TextField(
        label="Профиль / статус",
        value=user["profile"],
        border_radius=10,
        color=colors["title"],
        label_style=ft.TextStyle(color=colors["label"]),
    )

    def _save_profile(e):
        # Сброс ошибок
        f_name.error_text = None
        f_number.error_text = None
        f_name.border_color = None
        f_number.border_color = None
        page.update()

        # Собираем данные (сервер ждёт login, number, status)
        data = {
            "id":      user["id"],
            "token":   user["token"],
            "login":   f_name.value.strip(),
            "number":  f_number.value.strip(),
            "status":  f_profile.value.strip(),
        }

        try:
            resp = http.post(PROFILE_UPDATE_URL, json=data, timeout=10)
            body = resp.json()

            # Успех (код 200)
            if resp.status_code == 200 and body.get("post") == 200:
                # Обновляем локальную БД
                with sql.connect(db_path) as con:
                    cur = con.cursor()
                    cur.execute(
                        "UPDATE users_data SET name=?, profile=?, number=? WHERE id_user=?",
                        (data["login"], data["status"], data["number"], data["id"])
                    )
                    con.commit()

                # Обновляем словарь user и UI динамически
                user["name"]    = data["login"]
                user["profile"] = data["status"]
                user["number"]  = data["number"]
                name_text.value       = data["login"] or "Пользователь"
                profile_text.value    = data["status"] or ""
                
                # Закрываем диалог
                edit_dlg.open = False
                
                # Обновляем все цвета
                update_all_colors()
                
                # Уведомление об успехе
                page.snack_bar = ft.SnackBar(ft.Text("Данные изменены"), open=True)
                page.update()
                return

            # Обработка ошибок сервера (из поля error)
            error_msg = body.get("error", "")
            
            if "404_Login_already_covered" in error_msg:
                f_name.error_text = "Имя пользователя недоступно"
                f_name.border_color = ft.Colors.RED
                
            elif "404_Number_already_covered" in error_msg:
                f_number.error_text = "Номер уже используется другим аккаунтом"
                f_number.border_color = ft.Colors.RED
                
            elif "Неверный токен" in body.get("meaning", ""):
                page.snack_bar = ft.SnackBar(
                    ft.Text("Ошибка авторизации. Войдите заново."), open=True
                )
                
            else:
                # Другие ошибки
                meaning = body.get("meaning", "Неизвестная ошибка")
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Ошибка: {meaning}"), open=True
                )
            page.update()

        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Ошибка сети: {str(ex)[:100]}"), open=True
            )
            page.update()

    edit_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Редактировать профиль", color=colors["title"]),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Stack(
                        [
                            ft.Container(
                                content=ft.CircleAvatar(
                                    foreground_image_src="image/user.png",
                                    radius=45,
                                ),
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(
                                content=ft.IconButton(
                                    ft.Icons.ADD_A_PHOTO,
                                    icon_color=ft.Colors.WHITE,
                                    icon_size=18,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.BLUE,
                                        shape=ft.CircleBorder(),
                                        padding=ft.padding.all(4),
                                    ),
                                    on_click=lambda e: None,
                                ),
                                alignment=ft.alignment.bottom_right,
                                right=55, bottom=0,
                            ),
                        ],
                        width=120, height=100,
                    ),
                    f_name,
                    f_number,
                    f_profile,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            width=300,
            padding=ft.padding.only(top=8),
        ),
        actions=[
            ft.TextButton("Сохранить",
                          style=ft.ButtonStyle(color=ft.Colors.GREEN),
                          on_click=_save_profile),
            ft.TextButton("Отмена",
                          on_click=lambda e: (setattr(edit_dlg, "open", False), page.update())),
        ],
    )
    page.overlay.append(edit_dlg)

    # ── Шапка профиля ─────────────────────────────────────────────────────

    name_text = ft.Text(
        user["name"] or "Пользователь",
        weight=ft.FontWeight.BOLD, size=22,
        text_align=ft.TextAlign.CENTER,
        color=colors["title"],
    )
    profile_text = ft.Text(
        user["profile"] or "",
        size=14,
        text_align=ft.TextAlign.CENTER,
        color=colors["subtitle"],
    )

    def _open_edit_dialog(e):
        setattr(edit_dlg, "open", True)
        update_all_colors()

    profile_header = ft.Container(
        content=ft.Column(
            [
                ft.Stack(
                    [
                        ft.Container(
                            content=ft.CircleAvatar(
                                foreground_image_src="image/user.png",
                                radius=50,
                            ),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.IconButton(
                                ft.Icons.EDIT,
                                icon_color=ft.Colors.WHITE,
                                icon_size=16,
                                tooltip="Редактировать профиль",
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.BLUE_600,
                                    shape=ft.CircleBorder(),
                                    padding=ft.padding.all(4),
                                ),
                                on_click=_open_edit_dialog,
                            ),
                            alignment=ft.alignment.bottom_right,
                            right=0, bottom=0,
                        ),
                    ],
                    width=110, height=105,
                ),
                name_text,
                profile_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=20),
    )

    # ── Смена темы ─────────────────────────────────────────────────────────

    theme_icon = ft.Icon(
        ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE,
        color=colors["label"],
    )
    theme_title = ft.Text(
        "Тема оформления",
        size=16,
        weight=ft.FontWeight.W_500,
        color=colors["title"],
    )
    theme_label = ft.Text(
        "Тёмная тема" if is_dark else "Светлая тема",
        size=14,
        color=colors["label"],
    )

    def _toggle_theme(e):
        nonlocal is_dark
        is_dark = e.control.value
        new_theme = "dark" if is_dark else "light"
        
        # ЭТО СОХРАНЯЕТ В БД
        with sql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE user_settings SET color_theme = ?", (new_theme,))
            con.commit()
        
        # Обновляем интерфейс
        theme_label.value = "Тёмная тема" if is_dark else "Светлая тема"
        theme_icon.name = ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        update_all_colors()

    theme_row = ft.Container(
        content=ft.Row(
            [
                theme_icon,
                ft.Column(
                    [
                        theme_title,
                        theme_label,
                    ],
                    spacing=2, expand=True,
                ),
                ft.Switch(
                    value=is_dark,
                    on_change=_toggle_theme,
                    active_track_color=ft.Colors.BLUE_700,
                    thumb_color=ft.Colors.WHITE,
                    inactive_track_color=ft.Colors.GREY,
                ),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border_radius=12,
    )

    # ── Размер шрифта ─────────────────────────────────────────────────────

    font_icon = ft.Icon(
        ft.Icons.TEXT_FIELDS,
        color=colors["label"],
    )
    font_title = ft.Text(
        "Размер шрифта",
        size=16,
        weight=ft.FontWeight.W_500,
        color=colors["title"],
    )
    font_size_val = settings["font_size"]
    font_size_lbl = ft.Text(f"{font_size_val} px", size=13, color=colors["label"])
    font_preview  = ft.Text(
        "Пример текста сообщения",
        size=font_size_val,
        color=colors["label"],
        text_align=ft.TextAlign.CENTER,
    )

    def _change_font(e):
        val = int(e.control.value)
        
        # ЭТО СОХРАНЯЕТ В БД
        with sql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE user_settings SET font_size = ?", (str(val),))
            con.commit()
        
        # Обновляем интерфейс
        font_preview.size = val
        font_size_lbl.value = f"{val} px"
        page.update()

    font_row = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        font_icon,
                        ft.Column(
                            [
                                font_title,
                                font_size_lbl,
                            ],
                            spacing=2, expand=True,
                        ),
                    ],
                    spacing=14,
                ),
                ft.Slider(
                    value=font_size_val,
                    min=11, max=22, divisions=11,
                    label="{value} px",
                    active_color=ft.Colors.BLUE_700,
                    on_change=_change_font,
                ),
                ft.Container(
                    content=font_preview,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=4),
                ),
            ],
            spacing=4,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border_radius=12,
    )

    # ── Удаление аккаунта ─────────────────────────────────────────────────

    danger_icon = ft.Icon(ft.Icons.WARNING, color=ft.Colors.RED)
    danger_title = ft.Text(
        "Удалить аккаунт",
        size=16,
        weight=ft.FontWeight.W_500,
        color=ft.Colors.RED,
    )

    def _delete_account(e):
        # Диалог подтверждения
        confirm_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удаление аккаунта", color=colors["title"]),
            content=ft.Text(
                "Вы уверены, что хотите удалить свой аккаунт? Это действие необратимо.",
                color=colors["title"],
            ),
            actions=[
                ft.TextButton(
                    "Да",
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                    on_click=lambda _: _perform_delete()
                ),
                ft.TextButton(
                    "Нет",
                    on_click=lambda _: (
                        setattr(confirm_dlg, "open", False),
                        page.update()
                    )
                ),
            ],
        )
        page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        page.update()

    def _perform_delete():
        # Закрываем диалог подтверждения
        for overlay in page.overlay[:]:
            if isinstance(overlay, ft.AlertDialog) and overlay.title and \
               overlay.title.value == "Удаление аккаунта":
                overlay.open = False
                break

        page.update()
        try:
            resp = http.post(
                ACCOUNT_DELETE_URL,
                json={"id": user["id"], "token": user["token"]},
                timeout=10
            )
            # Проверяем успешный ответ (сервер возвращает 200 без тела)
            if resp.status_code == 200:
                # Удаляем локальные данные
                from app.components.database import delete_user_and_contacts
                delete_user_and_contacts(db_path)
                page.go('/login')
            else:
                # Обрабатываем ошибки от сервера
                try:
                    body = resp.json()
                    error_msg = body.get("error", "Ошибка при удалении")
                except:
                    error_msg = "Не удалось удалить аккаунт"
                
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Ошибка: {error_msg}"),
                    open=True,
                )
                page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Ошибка сети: {str(ex)[:100]}"), open=True
            )
            page.update()

    delete_btn = ft.OutlinedButton(
        icon=ft.Icons.DELETE_FOREVER,
        style=ft.ButtonStyle(color=ft.Colors.RED),
        on_click=_delete_account,
    )

    # ── Сборка ─────────────────────────────────────────────────────────────

    content = ft.Column(
        controls=[
            profile_header,
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column(
                    [
                        theme_row,
                        ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                        font_row,
                        ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                        ft.Container(
                            content=ft.Row(
                                [
                                    danger_icon,
                                    danger_title,
                                    ft.Container(expand=True),
                                    delete_btn,
                                ],
                                spacing=14,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        ),
                    ],
                    spacing=0,
                ),
                margin=ft.margin.symmetric(horizontal=8, vertical=8),
                border_radius=14,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            ),
        ],
        expand=True,
        spacing=0,
        scroll=ft.ScrollMode.ADAPTIVE,
    )

    appbar = ft.AppBar(
        leading=ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: page.go("/")),
        leading_width=40,
        title=ft.Text("Настройки", color=colors["title"]),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )

    return ft.View(
        "/settings",
        appbar=appbar,
        controls=[content],
    )