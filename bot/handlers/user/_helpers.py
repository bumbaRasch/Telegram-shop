import os
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, FSInputFile, InputMediaPhoto

# ── Photo cache (path → Telegram file_id) ──────────────────────────────────
_PHOTO_CACHE: dict[str, str] = {}

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'assets')
MENU_PHOTO_PATH  = os.path.join(_BASE, 'placeholder-image.png')
ADMIN_PHOTO_PATH = os.path.join(_BASE, 'placeholder-admin-image.png')


def get_photo(path: str):
    """Return cached file_id if available, otherwise an FSInputFile."""
    return _PHOTO_CACHE.get(path) or FSInputFile(path)


def cache_photo(path: str, file_id: str) -> None:
    _PHOTO_CACHE[path] = file_id


# ── Message edit helpers ────────────────────────────────────────────────────

async def edit_msg(message: Message, text: str, reply_markup=None,
                   parse_mode: str = 'HTML') -> None:
    """
    Edit text or caption — whichever fits the message type.
    Defaults to HTML parse_mode because most i18n strings contain <b>/<s> tags.
    """
    try:
        if message.photo or message.video or message.animation:
            await message.edit_caption(caption=text, reply_markup=reply_markup,
                                       parse_mode=parse_mode)
        else:
            await message.edit_text(text, reply_markup=reply_markup,
                                    parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def edit_media_msg(message: Message, photo_path: str, caption: str,
                         reply_markup=None, parse_mode: str = 'HTML') -> None:
    """
    Swap the photo of a photo-message and update caption + keyboard at once.
    Caches the returned file_id so subsequent swaps avoid re-uploading.
    """
    photo = get_photo(photo_path)
    try:
        result = await message.edit_media(
            media=InputMediaPhoto(media=photo, caption=caption, parse_mode=parse_mode),
            reply_markup=reply_markup,
        )
        if result and result.photo:
            cache_photo(photo_path, result.photo[-1].file_id)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
