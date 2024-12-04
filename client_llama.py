from db import connect_to_db, execute_query
from llama import request_to_lamma
from time import sleep
from json import dumps as json_dumps
from json import loads as json_loads


def get_unanswered_text() -> list:
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "select id, history, last_msg_id from dialog where is_answered = %s limit 1"
    params = ('false',)
    res = execute_query(conn, cursor, query, params)
    return res


def update_dialog_from_llama(dialog_id, text: list):
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "update dialog set history = %s, is_answered = %s, last_msg_id = %s where id = %s"
    params = (json_dumps(text), 'true', 0, dialog_id,)
    execute_query(conn, cursor, query, params)


def main():
    correction_prompt = (
    "Работай с текстом строго по инструкциям. Ни при каких условиях нельзя пересказывать текст "
    "или излагать его другими словами. Твоя задача — выделить ключевые тезисы и провести их анализ "
    "на достоверность. Формат твоего ответа начинается после блока [ФОРМАТ ОТВЕТА] (без написания '[ФОРМАТ ОТВЕТА]'), не раньше.\n"  # Работай только с утверждениями, содержащими факты или значимые события, которые можно проверить.
    "Из текста выдели ключевые тезисы:\n"
    "   - Тезисы должны быть четкими и краткими, содержать фактическую информацию.\n"
    "   - Каждый тезис — это отдельное утверждение или факт.\n\n"
    "[ФОРМАТ ОТВЕТА] Проведи анализ каждого тезиса:\n"
    "   - Проверь достоверность, исходя из известных фактов и логики.\n"
    "   - Укажи статус:\n"
    "     - **Достоверный**, если информация подтверждается.\n"
    "     - **Сомнительный**, если есть сомнения или недостаточно данных для проверки.\n"
    "     - **Неверный**, если информация противоречит известным данным.\n"
    "   - Обоснование: объясни, почему ты сделал такой вывод.\n\n"
    "Формат ответа строго следующий:\n"
    "- Тезис 1: [формулировка тезиса]\n"
    "  Анализ: [достоверный/сомнительный/неверный]\n"
    "  Обоснование: [почему сделан этот вывод].\n"
    "- Тезис 2: [формулировка тезиса]\n"
    "  Анализ: [достоверный/сомнительный/неверный]\n"
    "  Обоснование: [почему сделан этот вывод].\n"
    "- ...\n\n"
    "Запрещено:\n"
    "- Пересказывать текст или изменять его формулировки.\n"
    "- Приводить пересказ текста вместо выделения тезисов.\n"
    "- Добавлять собственные домыслы или несуществующие данные.\n"
    "Работай только с фактами из исходного текста."
    )

    while True:
        text_for_retell = get_unanswered_text()
        if text_for_retell:
            if text_for_retell[0][2] == 0:
                history = request_to_lamma(text_for_retell[0][1])
                update_dialog_from_llama(text_for_retell[0][0], history)
                history.append({
                    "role": "user",
                    "content": correction_prompt
                })
                history = request_to_lamma(history, False)
                update_dialog_from_llama(text_for_retell[0][0], history)
            elif text_for_retell[0][2] == -1:
                history = request_to_lamma(json_loads(text_for_retell[0][1]), False)
                update_dialog_from_llama(text_for_retell[0][0], history)
        sleep(10)


if __name__ == '__main__':
    main()
