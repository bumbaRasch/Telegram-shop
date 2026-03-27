import datetime
import functools

from aiogram import F, Router
from aiogram.enums.chat_type import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.methods import (
    check_role,
    check_user,
    check_user_cached,
    create_user,
    select_max_role_id,
    select_user_items,
    select_user_operations,
)
from bot.database.methods.lazy_queries import query_user_operations_history
from bot.database.methods.read import get_cart_count, get_setting
from bot.handlers.other import _parse_channel_username, check_sub_channel
from bot.handlers.user._helpers import MENU_PHOTO_PATH, cache_photo, edit_media_msg, edit_msg, get_photo
from bot.i18n import localize
from bot.keyboards import back, check_sub, main_menu, profile_keyboard
from bot.logger_mesh import logger
from bot.misc import EnvKeys, LazyPaginator
from bot.misc.metrics import get_metrics

router = Router()


@router.message(F.text.startswith("/start"))
async def start(message: Message, state: FSMContext):
    """
    Handle /start:
    - Ensure user exists (register if new)
    - (Optional) Check channel subscription
    - Show the main menu
    """
    if message.chat.type != ChatType.PRIVATE:
        return

    user_id = message.from_user.id
    await state.clear()

    owner_max_role = await select_max_role_id()
    referral_id = message.text[7:] if message.text[7:] != str(user_id) else None
    user_role = owner_max_role if user_id == EnvKeys.OWNER_ID else 1

    is_new_user = (await check_user(user_id)) is None

    # registration_date is DateTime
    await create_user(
        telegram_id=int(user_id),
        registration_date=datetime.datetime.now(datetime.UTC),
        referral_id=int(referral_id) if referral_id else None,
        role=user_role,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    if is_new_user:
        metrics = get_metrics()
        if metrics:
            metrics.track_event("registration", user_id)

    channel_username = _parse_channel_username()
    role_data = await check_role(user_id)

    # Optional subscription check
    try:
        if channel_username:
            chat_id = int(EnvKeys.CHANNEL_ID) if EnvKeys.CHANNEL_ID else f"@{channel_username}"
            chat_member = await message.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if not await check_sub_channel(chat_member):
                markup = check_sub(channel_username)
                await message.answer(localize("subscribe.prompt"), reply_markup=markup)
                await message.delete()
                return
    except Exception as e:
        # Ignore all channel check errors (private channel, wrong link, network, etc.)
        # On error fall through and show the menu — better than leaving user with empty screen
        logger.warning(f"Channel subscription check failed for user {user_id}: {e}")

    layout = await get_setting("menu_layout", "1")
    markup = main_menu(role=role_data, channel=channel_username, helper=EnvKeys.HELPER_ID, layout=layout)
    photo = get_photo(MENU_PHOTO_PATH)
    try:
        sent = await message.answer_photo(photo, caption=localize("menu.title"), reply_markup=markup, parse_mode="HTML")
        if sent.photo:
            cache_photo(MENU_PHOTO_PATH, sent.photo[-1].file_id)
    except Exception:
        await message.answer(localize("menu.title"), reply_markup=markup, parse_mode="HTML")
    await message.delete()
    await state.clear()


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback_handler(call: CallbackQuery, state: FSMContext):
    """
    Return user to the main menu.
    """
    user_id = call.from_user.id
    user = await check_user_cached(user_id)
    if not user:
        await create_user(
            telegram_id=user_id,
            registration_date=datetime.datetime.now(datetime.UTC),
            referral_id=None,
            role=1,
            username=call.from_user.username,
            first_name=call.from_user.first_name,
            last_name=call.from_user.last_name,
        )
        user = await check_user_cached(user_id)

    role_id = user.get("role_id")

    channel_username = _parse_channel_username()
    layout = await get_setting("menu_layout", "1")
    markup = main_menu(role=role_id, channel=channel_username, helper=EnvKeys.HELPER_ID, layout=layout)
    await edit_media_msg(call.message, MENU_PHOTO_PATH, localize("menu.title"), markup)
    await state.clear()


@router.callback_query(F.data == "rules")
async def rules_callback_handler(call: CallbackQuery, state: FSMContext):
    """
    Show rules text if provided in ENV.
    """
    rules_data = EnvKeys.RULES
    if rules_data:
        await edit_msg(call.message, rules_data, back("back_to_menu"))
    else:
        await call.answer(localize("rules.not_set"))
    await state.clear()


@router.callback_query(F.data == "profile")
async def profile_callback_handler(call: CallbackQuery, state: FSMContext):
    """
    Send profile info (balance, purchases count, id, etc.).
    """
    user_id = call.from_user.id
    tg_user = call.from_user
    user_info = await check_user_cached(user_id)

    balance = user_info.get("balance")
    operations = await select_user_operations(user_id)
    overall_balance = sum(operations) if operations else 0
    items = await select_user_items(user_id)
    referral = EnvKeys.REFERRAL_PERCENT
    cart_count = await get_cart_count(user_id)

    markup = profile_keyboard(referral, items, cart_count=cart_count)
    text = (
        f"{localize('profile.caption', name=tg_user.first_name, id=user_id)}\n"
        f"{localize('profile.id', id=user_id)}\n"
        f"{localize('profile.balance', amount=balance, currency=EnvKeys.PAY_CURRENCY)}\n"
        f"{localize('profile.total_topup', amount=overall_balance, currency=EnvKeys.PAY_CURRENCY)}\n"
        f"{localize('profile.purchased_count', count=items)}"
    )
    await edit_msg(call.message, text, markup, parse_mode="HTML")
    await state.clear()


@router.callback_query(F.data == "sub_channel_done")
async def check_sub_to_channel(call: CallbackQuery, state: FSMContext):
    """
    Re-check channel subscription after user clicks "Check".
    """
    user_id = call.from_user.id
    channel_username = _parse_channel_username()
    helper = EnvKeys.HELPER_ID

    if channel_username:
        chat_id = int(EnvKeys.CHANNEL_ID) if EnvKeys.CHANNEL_ID else f"@{channel_username}"
        chat_member = await call.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if await check_sub_channel(chat_member):
            user = await check_user_cached(user_id)
            role_id = user.get("role_id")
            layout = await get_setting("menu_layout", "1")
            markup = main_menu(role_id, channel_username, helper, layout=layout)
            await edit_media_msg(call.message, MENU_PHOTO_PATH, localize("menu.title"), markup)
            await state.clear()
            return

    await call.answer(localize("errors.not_subscribed"))


# --- Operation History ---


@router.callback_query(F.data == "operation_history")
async def operation_history_handler(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    await _show_operations_page(call, state, user_id, 0)


@router.callback_query(F.data.startswith("ops-page_"))
async def navigate_operations(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split("_")[1])
    await _show_operations_page(call, state, call.from_user.id, page)


async def _show_operations_page(call: CallbackQuery, state: FSMContext, user_id: int, page: int):
    paginator = LazyPaginator(functools.partial(query_user_operations_history, user_id), per_page=10)
    items = await paginator.get_page(page)
    total_pages = await paginator.get_total_pages()

    if not items:
        await edit_msg(call.message, localize("history.title") + "\n\n" + localize("history.empty"), back("profile"))
        return

    lines = [localize("history.title"), ""]
    for op in items:
        op_type = op["type"]
        amount = op["amount"]
        date = op["date"]
        date_str = str(date)[:19] if date else ""

        if op_type == "topup":
            lines.append(localize("history.topup", amount=amount, currency=EnvKeys.PAY_CURRENCY))
        elif op_type == "purchase":
            lines.append(localize("history.purchase", amount=amount, currency=EnvKeys.PAY_CURRENCY))
        elif op_type == "referral":
            lines.append(localize("history.referral", amount=amount, currency=EnvKeys.PAY_CURRENCY))
        lines.append(localize("history.date", date=date_str))
        lines.append("")

    kb = InlineKeyboardBuilder()
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"ops-page_{page - 1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"ops-page_{page + 1}"))
    if nav_buttons:
        kb.row(*nav_buttons)
    kb.row(InlineKeyboardButton(text=localize("btn.back"), callback_data="profile"))

    await edit_msg(call.message, "\n".join(lines), kb.as_markup())
