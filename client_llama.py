from db import connect_to_db, execute_query
from llama import request_to_lamma
from time import sleep


def get_unanswered_text():
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "select id, history, last_msg_id from dialog where is_answered = %s limit 1"
    params = ('false',)
    res = execute_query(conn, cursor, query, params)
    return res


def update_dialog_from_llama(dialog_id, text, is_initiation=True):
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    if is_initiation:
        query = "update dialog set history = %s, is_answered = %s where id = %s"
        params = (text, 'true', dialog_id,)
    else:
        query = "update dialog set history = %s, is_answered = %s, last_msg_id = %s where id = %s"
        params = (text, 'true', 0, dialog_id,)
    execute_query(conn, cursor, query, params)


def main():
    while True:
        text_for_retell = get_unanswered_text()
        if text_for_retell:
            if text_for_retell[0][2] == 0:
                retell, history = request_to_lamma(text_for_retell[0][1])
                update_dialog_from_llama(text_for_retell[0][0], str(history))
            elif text_for_retell[0][2] == -1:
                retell, history = request_to_lamma(eval(text_for_retell[0][1]), False)
                update_dialog_from_llama(text_for_retell[0][0], str(history), False)
        sleep(10)


if __name__ == '__main__':
    main()
