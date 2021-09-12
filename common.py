import csv
import json
import os
import random
import re
import unicodedata
from typing import Any, Dict, List, Union

from parsers.PCs import PCData

remove_letters = re.compile(r"™®")

# items_file = "all_items.json"
# out_file = "all_items.csv"
# excel_file = "all_items.xlsx"
# excel_json = "excel_data.json"
items_file = "items_{}.json"

website = "https://www.amazon.ae"
search_endpoint = "s"
endpoint = f"{website}/{search_endpoint}"


def roundup(number):
    return int((int(number) + 9) // 10 * 10)


def load_items() -> Dict:
    file = open(items_file, encoding="utf-8")
    data = json.load(file)
    file.close()
    return data


def load_excel_json() -> List[PCData]:
    file = open(excel_json, encoding="utf-8")
    data = json.load(file)
    file.close()
    return data


def get_writer():
    return csv.writer(open(out_file, "w+", encoding="utf-8", newline=""))


def get_random_dict_item(dict_: Dict) -> Any:
    keys = list(dict_.keys())
    return dict_[random.choice(keys)]


def save_json(dict_: Any, file_path: str):
    with open(file_path, "w+", encoding="utf-8") as file:
        json.dump(dict_, file, indent=4)


def capitalize_all(string: str):
    return " ".join([s.capitalize() for s in string.split()])


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def get_pages(rows: Union[str, list], idx: int = None):
    br = Chrome()
    if isinstance(rows, str):
        rows = [rows]
    for row in rows:
        if idx == -1:
            *_, url = row
        elif idx:
            url = row[idx]
        else:
            url = rows[0]
        file_path = f"pages/{slugify(url)}.html"
        if os.path.isfile(file_path):
            continue
        br.get(url)
        with open(file_path, "wb") as file:
            file.write(br.page_source.encode())

    br.close()
    br.quit()
