import asyncio
from aiogram import Bot, Dispatcher, types
from db import connect_to_db, execute_query
# from aiogram.filters import Command
from json import dumps as json_dumps
from json import loads as json_loads
import re
import os
from dotenv import load_dotenv


load_dotenv()
bot_token = os.getenv('bot_token')
bot = Bot(token=bot_token)
dp = Dispatcher()
think_pattern = r"<think>(.*?)</think>"  # For DeepSeek thinking


async def get_answered_text():
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "select id, history from dialog where is_answered = %s and last_msg_id = %s limit 1;"
    params = ('true', '0',)
    res = execute_query(conn, cursor, query, params)
    if res:
        id_dialog = res[0][0]
        res = json_loads(res[0][1])
        res = res[-1]['content']
        return [res, id_dialog]
    return False


async def answer_update_dialog(id_dialog: int, last_msg_id: int):
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "update dialog set last_msg_id = %s where id = %s"
    params = (last_msg_id, id_dialog,)
    execute_query(conn, cursor, query, params)


async def user_update_dialog(last_msg_id: int, user_text: str):
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "select id, history from dialog where last_msg_id = %s"
    params = (last_msg_id,)
    res = execute_query(conn, cursor, query, params)
    if res:
        id_dialog = res[0][0]
        dialog_history = res[0][1]
        dialog_history = json_loads(dialog_history)
        dialog_history.append({
            "role": "user",
            "content": user_text,
        })
        dialog_history = json_dumps(dialog_history)
        conn = connect_to_db()
        cursor = conn.cursor()
        query = "update dialog set is_answered = %s, history = %s, last_msg_id = %s where id = %s"
        params = ('false', dialog_history, -1, id_dialog,)
        execute_query(conn, cursor, query, params)
        return True
    else:
        return False


async def split_text_to_chunks(text, max_length=4095):
    # Инициализируем пустой список для хранения отрывков текста
    chunks = []

    # Разделяем текст по длине max_length
    while len(text) > max_length:
        # Находим последнее место для разреза по пробелу в пределах max_length
        split_index = text[:max_length].rfind(" ")
        if split_index == -1:  # если пробела нет, режем точно по max_length
            split_index = max_length

        # Добавляем часть текста в список и обрезаем исходный текст
        chunks.append(text[:split_index])
        text = text[split_index:].lstrip()  # убираем лишние пробелы слева у оставшегося текста

    # Добавляем оставшийся текст как последний отрывок
    chunks.append(text)
    return chunks


def escape_md_v2_custom(text: str) -> str:
    """
    Экранирует текст для MarkdownV2, но оставляет нужные символы форматирования (*, _, > и т.д.)
    """
    text = text.replace('#', '')
    escape_chars = r'([]()~`+=|{}.!-)'
    return re.sub(r'(?<!\\)([' + re.escape(escape_chars) + r'])', r'\\\1', text)


def convert_to_quote(match):
    """
    Заворачивает блок текста в цитату для re.sub()
    """
    inner_text = match.group(1).strip()
    text_lines = inner_text.splitlines()
    quoted_text = f"**>{text_lines[0]}\n"
    quoted_text += "\n".join([">" + line for line in text_lines[1:]])
    return quoted_text


async def send_answered_text(chat_id: int):
    """
    Функция отправки сообщения и вызова обновления диалога.
    """
    res_query = await get_answered_text()
    if res_query is not False:
        id_dialog = res_query[1]
        text_to_send = res_query[0]
        text_to_send = re.sub(think_pattern, convert_to_quote, text_to_send, flags=re.DOTALL)
        text_to_send = escape_md_v2_custom(text_to_send)

        if len(text_to_send) > 4094:
            text_to_send_chunks = await split_text_to_chunks(text_to_send)
            for chunk in text_to_send_chunks:
                await asyncio.sleep(3)
                try:  # Обработчики на случай, если MdV2 даст ошибку экранирования
                    sent_message = await bot.send_message(chat_id=chat_id, text=chunk, parse_mode='MarkdownV2')
                except Exception as e:
                    await bot.send_message(chat_id=chat_id, text=f'Ошибка при отправке с парсингом, попытка отправить без парсинга:\n{e}')
                    await asyncio.sleep(3)
                    sent_message = await bot.send_message(chat_id=chat_id, text=chunk)
        else:
            try:  # Обработчики на случай, если MdV2 даст ошибку экранирования
                sent_message = await bot.send_message(chat_id=chat_id, text=text_to_send, parse_mode='MarkdownV2')
            except Exception as e:
                await bot.send_message(chat_id=chat_id, text=f'Ошибка при отправке с парсингом, попытка отправить без парсинга:\n{e}')
                await asyncio.sleep(3)
                sent_message = await bot.send_message(chat_id=chat_id, text=text_to_send)

        await answer_update_dialog(id_dialog, sent_message.message_id)


@dp.message()
async def handle_user_message(message: types.Message):
    """
    Передача уточнений пользователя в продолжаемый диалог
    """
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        last_msg_id = message.reply_to_message.message_id
        user_text = message.text
        status = await user_update_dialog(last_msg_id, user_text)
        if not status:
            await message.reply('Данной переписки больше нет в БД')
    else:
        await message.reply("Пожалуйста, ответьте на сообщение бота, чтобы продолжить")


async def periodic_task(chat_id: int):
    """
    Запуск периодической отправки сообщений
    """
    while True:
        await send_answered_text(chat_id)
        await asyncio.sleep(10)


async def clear_db():
    """
    Очистка бд от нетронутых диалогов в течении 3-х дней
    """
    while True:
        conn = connect_to_db()
        cursor = conn.cursor()
        query = "delete from dialog where date < NOW() - INTERVAL '3 days';"
        execute_query(conn, cursor, query)
        await asyncio.sleep(60*60*12)


# async def send_welcome(message: types.Message):
#     """
#     Обработчик команды /start.
#     """
#     await message.answer("Привет! Я бот, который будет отправлять сообщения и обновлять диалоги.")


async def main():
    asyncio.create_task(periodic_task(538231919))
    asyncio.create_task(clear_db())

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
