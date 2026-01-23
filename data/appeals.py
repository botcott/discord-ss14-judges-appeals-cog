import os
import json
import logging
import datetime

async def save_data(judge_id: int, appeal_id: int, filename = f"{os.path.dirname(__file__)}/appeals.json") -> None:
    data = {}
    if (os.path.exists(filename)):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}

    judge_id = str(judge_id)

    now = datetime.datetime.now()
    time = now.strftime("%m.%Y.%H.%M.%S")

    if (judge_id in data):
        if ("appeals" in data[judge_id] and "appeals" in data[judge_id]["appeals"] and isinstance(data[judge_id]["appeals"]["appeals"], list)):
            if (appeal_id not in data[judge_id]["appeals"]["appeals"]):
                data[judge_id]["appeals"]["appeals"].append(appeal_id)
                data[judge_id]["appeals"]["message_time"].append(time)

        else:
            data[judge_id]["appeals"] = {"appeals": [appeal_id], "message_time": [time]}
    else:
        data[judge_id] = {"appeals": {"appeals": [appeal_id], "message_time": [time]}}

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

async def remove_data(judge_id: int, appeal_id: int, filename=f"{os.path.dirname(__file__)}/appeals.json") -> None:
    if (not os.path.exists(filename)):
        logging.info(f"Файл {filename} не существует.")
        return

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Ошибка: Не удалось загрузить JSON из файла {filename}. Файл может быть поврежден или отсутствует. Ошибка: {e}")
        return

    judge_id_str = str(judge_id)

    if (judge_id_str not in data):
        logging.warning(f"Предупреждение: judge_id {judge_id} не найден в файле {filename}.")
        return

    if (not "appeals" in data[judge_id_str] and isinstance(data[judge_id_str]["appeals"], dict) and
            "appeals" in data[judge_id_str]["appeals"] and isinstance(data[judge_id_str]["appeals"]["appeals"], list)):
        return
    
    try:
        appeal_index = data[judge_id_str]["appeals"]["appeals"].index(appeal_id)

        removed_appeal = data[judge_id_str]["appeals"]["appeals"].pop(appeal_index)
        removed_appeal_time = data[judge_id_str]["appeals"]["message_time"].pop(appeal_index)

        now = datetime.datetime.now()
        closing_time = now.strftime("%m.%Y.%H.%M.%S")

        logging.info(f"appeal_id {appeal_id} удалён")

    except ValueError:
        logging.warning(f"Предупреждение: appeal_id {appeal_id} не найден")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Ошибка: Не удалось записать данные в файл {filename}: {e}")

async def check_appeal(appeal_id: int, filename = f"{os.path.dirname(__file__)}/appeals.json") -> bool:
    if (not os.path.exists(filename)):
        logging.info(f"Файл {filename} не существует.")
        return False

    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except Exception:
        return False

    for judge_id, judge_data in data.items():
        if (isinstance(judge_data, dict) and "appeals" in judge_data and "appeals" in judge_data["appeals"] and "appeals" in judge_data["appeals"] and isinstance(judge_data["appeals"]["appeals"], list)):
            if (appeal_id in judge_data["appeals"]["appeals"]):
                return True

    logging.info(f"appeal_id {appeal_id} принят")
    return False

async def get_judge(appeal_id: int, filename = f"{os.path.dirname(__file__)}/appeals.json") -> bool | int | str:
    if (not os.path.exists(filename)):
        logging.info(f"Файл {filename} не существует.")
        return False

    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except Exception:
        return False

    for judge_id, judge_data in data.items():
        if (isinstance(judge_data, dict) and "appeals" in judge_data and "appeals" in judge_data["appeals"] and "appeals" in judge_data["appeals"] and isinstance(judge_data["appeals"]["appeals"], list)):
            if (appeal_id in judge_data["appeals"]["appeals"]):
                return judge_id

    logging.info(f"appeal_id {appeal_id} принят")
    return False

async def get_all_appeals(filename=f"{os.path.dirname(__file__)}/appeals.json") -> list:
    appeal_ids = []
    if (not os.path.exists(filename)):
        logging.info(f"Файл {filename} не существует.")
        return appeal_ids

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Ошибка: Не удалось загрузить JSON из файла {filename}. Файл может быть поврежден или отсутствует. Ошибка: {e}")
        return appeal_ids

    for judge_id, judge_data in data.items():
        if (isinstance(judge_data, dict) and "appeals" in judge_data and isinstance(judge_data["appeals"], dict) and "appeals" in judge_data["appeals"]):
            appeals_list = judge_data["appeals"]["appeals"]
            if (isinstance(appeals_list, list)):
                appeal_ids.extend(appeals_list)
            else:
                logging.warning(f"Неожиданный формат данных для judge_id {judge_id}. 'appeals' должен быть списком.")
        else:
            logging.warning(f"Неожиданный формат данных для judge_id {judge_id}. Пропущено.")

    return appeal_ids

async def calc_time(time_str1: str, time_str2: str) -> int | None:
    time_format = "%m.%Y.%H.%M.%S"
    try:
        time1 = datetime.datetime.strptime(time_str1, time_format)
        time2 = datetime.datetime.strptime(time_str2, time_format)
        diff = abs((time2 - time1).total_seconds())
        return diff
    except ValueError:
        logging.error("Ошибка: Неверный формат времени. Ожидается формат 'MM.YYYY.HH.mm.ss'")
        return None

async def update_time(judge_id: int, appeal_id: int, filename=f"{os.path.dirname(__file__)}/appeals.json") -> bool:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Ошибка: Не удалось загрузить JSON из файла {filename}. Файл может быть поврежден или отсутствует. Ошибка: {e}")
        return False

    judge_id_str = str(judge_id)

    if (judge_id_str in data):
        appeals_data = data[judge_id_str]["appeals"]
        if ("appeals" in appeals_data and "message_time" in appeals_data):
            appeals_list = appeals_data["appeals"]
            time_list = appeals_data["message_time"]

            try:
                appeal_index = appeals_list.index(appeal_id)
                now = datetime.datetime.now()
                new_time = now.strftime("%m.%Y.%H.%M.%S")

                time_list[appeal_index] = new_time

                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    return True
                except IOError as e:
                    logging.error(f"Ошибка: Не удалось сохранить JSON в файл {filename}. Ошибка: {e}")
                    return False

            except ValueError:
                logging.error(f"Ошибка: appeal_id {appeal_id} не найден в списке appeals для judge_id {judge_id}")
                return False
        else:
            return False
    else:
        logging.error(f"Ошибка: judge_id {judge_id} не найден в JSON")
        return False
    
async def get_time(judge_id: int, appeal_id: int, filename=f"{os.path.dirname(__file__)}/appeals.json") -> None | str:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Ошибка: Не удалось загрузить JSON из файла {filename}. Файл может быть поврежден или отсутствует. Ошибка: {e}")
        return None

    judge_id_str = str(judge_id)

    if (judge_id_str in data):
        appeals_data = data[judge_id_str]["appeals"]
        if ("appeals" in appeals_data and "message_time" in appeals_data):
            appeals_list = appeals_data["appeals"]
            time_list = appeals_data["message_time"]

            try:
                appeal_index = appeals_list.index(appeal_id)
                return time_list[appeal_index]

            except ValueError:
                return None
        else:
            return None
    else:
        logging.error(f"Ошибка: judge_id {judge_id} не найден в JSON.")
        return None

async def get_appeals_info(judge_id: int, filename=f"{os.path.dirname(__file__)}/appeals.json") -> dict:
    if (not os.path.exists(filename)):
        logging.error(f"Файл {filename} не существует.")
        return None

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Ошибка: Не удалось загрузить JSON из файла {filename}. Файл может быть поврежден или отсутствует. Ошибка: {e}")
        return None

    judge_id_str = str(judge_id)
    if (judge_id_str not in data):
        return None

    judge_data = data[judge_id_str]
    open_appeals = []
    closed_appeals = []

    if ("appeals" in judge_data and isinstance(judge_data["appeals"], dict) and "appeals" in judge_data["appeals"] and isinstance(judge_data["appeals"]["appeals"], list)):
        open_appeals = judge_data["appeals"]["appeals"]

    if ("closed_appeals" in judge_data and isinstance(judge_data["closed_appeals"], dict) and "appeals" in judge_data["closed_appeals"] and isinstance(judge_data["closed_appeals"]["appeals"], list)):
        closed_appeals = judge_data["closed_appeals"]["appeals"]

    return {
        "open_appeals": open_appeals,
        "closed_appeals": closed_appeals
    }
