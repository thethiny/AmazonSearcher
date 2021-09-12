import csv
import json
import os
import random
import re
import unicodedata
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

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


class DEPARTMENT(Enum):
    COMPUTERS = "computers"


class CATEGORY(Enum):
    # Computers
    LAPTOPS = 12050245031
    COMPUTER_PARTS = 11497745031
    #
    SSD = 11497745031
    EXTERNAL_STORAGE = 12050286031
    INTERNAL_COMPONENTS = 15144684031
    ##
    COMPUTER_FANS = 12050274031
    MOTHERBOARDS = 12050282031
    GPU = 12050275031
    CPU = 12050272031
    PSU = 12050284031
    RAM = 12050281031


class SHIPPING(Enum):
    SHIPPING_DOMESTIC = 20642115031
    SHIPPING_INTERNATIONAL = 20642116031
    SHIPPING_FULFILLED = 16258112031
    DELIVERY_SAME_DAY = 15397663031
    DELIVERY_NEXT_DAY = 15397664031
    ITEM_OUTOFSTOCK = 12407978031


class SORTING(Enum):
    PRICE = "price-asc-rank"
    PRICE_DESC = "price-desc-rank"
    FEATURED = "relevanceblender"
    REVIEWS = "review-rank"
    DATE = "date-desc-rank"


class RATING_FILTER(Enum):
    STARS_ONE = 12407975031
    STARS_TWO = 12407974031
    STARS_THREE = 12407973031
    STARS_FOUR = 12407972031


# Types
class DeliveryOptionsType(TypedDict):
    domestic: Optional[Literal[SHIPPING.SHIPPING_DOMESTIC]]
    international: Optional[Literal[SHIPPING.SHIPPING_INTERNATIONAL]]
    verified: Optional[Literal[SHIPPING.SHIPPING_FULFILLED]]
    same_day: Optional[Literal[SHIPPING.DELIVERY_SAME_DAY]]
    next_day: Optional[Literal[SHIPPING.DELIVERY_NEXT_DAY]]
    oos: Optional[Literal[SHIPPING.ITEM_OUTOFSTOCK]]


class CategoryInfoType(TypedDict):
    category: DEPARTMENT
    subcategory: CATEGORY


class SearchParamsType(TypedDict, total=False):
    i: str  # Category
    rh: str  # Filters
    s: str  # Sort
    k: str  # Keywords
