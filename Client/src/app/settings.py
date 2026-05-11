import flet as ft
import sqlite3 as sql
import path

db_path = f"{path.db_path()}user_data.db"


# ── БД ───────────────────────────────────────────────────────────────────────

def _migrate_settings():
    """Добавляет font_size если нет (color_theme уже есть в main.py)."""
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
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT name, profile, number, avatar FROM users_data LIMIT 1")
            row = cur.fetchone()
            if row:
                return {"name": row[0] or "", "profile": row[1] or "",
                        "number": row[2] or "", "avatar": row[3] or ""}
        except sql.OperationalError:
            pass
    return {"name": "", "profile": "", "number": "", "avatar": ""}


def _apply_font(page: ft.Page, size: int):
    """Обновляет размер шрифта в обеих темах страницы."""
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

    # ── Диалог редактирования профиля ─────────────────────────────────────────

    f_name    = ft.TextField(label="Имя",    value=user["name"],    border_radius=10)
    f_number  = ft.TextField(label="Номер",  value=user["number"],  border_radius=10,
                             keyboard_type=ft.KeyboardType.PHONE)
    f_profile = ft.TextField(label="Профиль / статус", value=user["profile"], border_radius=10)

    def _save_profile(e):
        # Логика сохранения будет добавлена позже
        edit_dlg.open = False
        page.update()

    edit_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Редактировать профиль"),
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
                                    on_click=lambda e: None,  # будет добавлено позже
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

    # ── Шапка профиля ─────────────────────────────────────────────────────────

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
                                on_click=lambda e: (
                                    setattr(edit_dlg, "open", True), page.update()
                                ),
                            ),
                            alignment=ft.alignment.bottom_right,
                            right=0, bottom=0,
                        ),
                    ],
                    width=110, height=105,
                ),
                ft.Text(user["name"] or "Пользователь",
                        weight=ft.FontWeight.BOLD, size=22,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(user["profile"] or "",
                        size=14, color=ft.Colors.GREY,
                        text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=20),
    )

    # ── Смена темы ────────────────────────────────────────────────────────────

    is_dark = settings["color_theme"] == "dark"

    theme_label = ft.Text(
        "Тёмная тема" if is_dark else "Светлая тема",
        size=14, color=ft.Colors.GREY,
    )

    def _toggle_theme(e):
        nonlocal is_dark
        is_dark = e.control.value
        new_theme = "dark" if is_dark else "light"
        _save_setting("color_theme", new_theme)
        theme_label.value = "Тёмная тема" if is_dark else "Светлая тема"
        page.theme_mode   = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.update()

    theme_row = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.DARK_MODE, color=ft.Colors.GREY),
                ft.Column(
                    [
                        ft.Text("Тема оформления", size=16, weight=ft.FontWeight.W_500),
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

    # ── Размер шрифта ─────────────────────────────────────────────────────────

    font_size_val = settings["font_size"]
    font_preview  = ft.Text(
        "Пример текста сообщения",
        size=font_size_val,
        color=ft.Colors.GREY,
        text_align=ft.TextAlign.CENTER,
    )
    font_size_lbl = ft.Text(f"{font_size_val} px", size=13, color=ft.Colors.GREY)

    def _change_font(e):
        val = int(e.control.value)
        _save_setting("font_size", str(val))
        font_preview.size   = val
        font_size_lbl.value = f"{val} px"
        # Применяем ко всему приложению сразу
        _apply_font(page, val)
        page.update()

    font_row = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.TEXT_FIELDS, color=ft.Colors.GREY),
                        ft.Column(
                            [
                                ft.Text("Размер шрифта", size=16, weight=ft.FontWeight.W_500),
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

    # ── Сборка ────────────────────────────────────────────────────────────────

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
        title=ft.Text("Настройки"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )

    return ft.View(
        "/settings",
        appbar=appbar,
        controls=[content],
    )