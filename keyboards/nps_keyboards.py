# filepath: keyboards/nps_keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_nps_keyboard(request_id: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f"⭐ {i}", callback_data=f"nps:{request_id}:{i}")
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def get_maps_keyboard(map_link_2gis: str | None, map_link_google: str | None) -> InlineKeyboardMarkup:
    keyboard = []
    if map_link_2gis:
        keyboard.append([InlineKeyboardButton(text="📍 Отзыв на 2GIS", url=map_link_2gis)])
    if map_link_google:
        keyboard.append([InlineKeyboardButton(text="🗺️ Отзыв на Google Maps", url=map_link_google)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)