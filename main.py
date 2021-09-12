import json
import os
import re
from typing import Any, List, Optional, Tuple
from urllib.parse import quote_plus

from bs4 import BeautifulSoup as soup
from bs4.element import Tag
from selenium.webdriver import Chrome

from common import (
    CATEGORY,
    DEPARTMENT,
    RATING_FILTER,
    SHIPPING,
    SORTING,
    CategoryInfoType,
    DeliveryOptionsType,
    endpoint,
    items_file,
    slugify,
)


class AmazonSearch:
    website = "https://www.amazon.ae"
    search_endpoint = "s"
    endpoint = f"{website}/{search_endpoint}"
    item_price_regex = re.compile(r"(" r"([0-9]+,?)+" r"(?:\.[0-9]+)?)")

    def __init__(
        self,
        category: DEPARTMENT = None,  # i=
        sub_category: CATEGORY = None,  # rh=n:
        prime_national: bool = False,  # rh=p_n_prime_domestic:
        prime_international: bool = False,  # rh=p_n_prime_domestic:
        min_price: float = None,  # rh=p_36:min-max
        max_price: float = None,  # rh=p_36:min-max
        sorting_method: SORTING = None,  # s=
        amazon_fulfilled: bool = False,  # rh=p_n_fulfilled_by_amazon:
        same_day_delivery: bool = False,  # rh=p_90:
        next_day_delivery: bool = False,  # rh=p_90:
        include_out_of_stock: bool = False,  # rh=p_n_availability:
        min_rating: int = 0,  # rh=p_72:
        keywords: str = "",
    ):
        self.category_info = self.set_category_options(category, sub_category)
        self.shipping_information = self.set_shipping_options(
            prime_national,
            prime_international,
            amazon_fulfilled,
            same_day_delivery,
            next_day_delivery,
            include_out_of_stock,
        )
        self.price_range = self.set_price_options(min_price, max_price)
        self.sorting_method = self.set_sorting_options(sorting_method)
        self.min_rating = self.set_rating_options(min_rating)
        self.keywords = self.set_keywords_filter(keywords)

        self.init_files(  # Needs to be changed to be parsed from current_internal
            prime_national,
            prime_international,
            amazon_fulfilled,
            same_day_delivery,
            next_day_delivery,
            include_out_of_stock,
            min_rating,
        )

    def set_keywords_filter(self, keywords: str):
        return keywords

    def init_files(self, *args):
        folder_structure = "AmazonData"
        if self.category_info["category"]:
            folder_structure = os.path.join(
                folder_structure, self.category_info["category"].value.capitalize()
            )
            if self.category_info["subcategory"]:
                folder_structure = os.path.join(
                    folder_structure,
                    self.category_info["subcategory"].name.capitalize(),
                )

        file_name = slugify(self.keywords) if self.keywords else ""
        file_name += f"_{self.price_range[0]}-{self.price_range[1]}"
        extra = "_".join([str(a) for a in args])
        file_name += f"_{extra}" if extra else ""
        file_name = items_file.format(file_name)

        try:
            os.makedirs(folder_structure)
        except (OSError, FileExistsError):
            pass

        self.file_name = os.path.join(folder_structure, file_name)
        self.file = open(self.file_name, "w+", encoding="utf-8")

    def make_url(self, endpoint):
        return f"{endpoint}{self.make_param_string()}{self.get_next_page_url()}"

    def get_page_items(self, page: Any):
        content = soup(page, features="lxml")
        search_results: Tag = content.find("span", {"data-component-type": "s-search-results"})  # type: ignore
        if not search_results:
            raise ValueError("Couldn't Locate Search Results!")

        items_container: Tag = search_results.find("div", class_="s-main-slot")  # type: ignore
        if not items_container:
            raise ValueError("No Search Results Found!")

        items: List[Tag] = items_container.find_all("div", {"data-uuid": True})  # type: ignore

        found_items = []
        for item in items:
            try:
                item_name = item.find("h2").text  # type: ignore
            except AttributeError:
                raise ValueError("Couldn't parse item name!")

            try:
                item_url = f'{self.__class__.website}{item.find("a")["href"]}'  # type: ignore
            except (KeyError, AttributeError):
                raise ValueError("Couldn't parse item url!")

            item_price_elem = item.find("span", class_="a-price")
            try:
                item_price = item_price_elem.find("span", {"aria-hidden": True}).text  # type: ignore
            except AttributeError:
                item_price = "0"
            found_items.append(
                [item_url, item_name.strip(), self.clean_item_price(item_price)]
            )
        return found_items

    @classmethod
    def clean_item_price(cls, item_price):
        price = cls.item_price_regex.search(item_price)
        if price:
            return float(price.group().replace(",", ""))
        return 0

    def write_data(self, data):
        data = json.dumps(data)
        self.file.write(data + "\n")

    def start(self):
        self.br = Chrome()

    def run(self):
        self.start()
        self.current_page = 0

        pages = 1

        while self.current_page < pages:
            url = self.make_url(endpoint)
            page = self.get_page(url)
            if self.current_page == 0:
                pages = self.get_pages_count(page)

            found_items = self.get_page_items(page)
            for item in found_items:
                self.write_data(item)

            self.current_page += 1

        self.shutdown()

    def get_next_page_url(self):
        return f"&page={self.current_page+1}"

    def get_page(self, url):
        self.br.get(url)
        return self.br.page_source

    def get_pages_count(self, content):
        content = soup(content)
        pagination: Tag = content.find(class_="a-pagination")  # type: ignore
        if not pagination:
            raise ValueError("Couldn't find Pagination!")
        max_page = 1
        for element in pagination.find_all("li"):
            try:
                element_text = element.text  # type: ignore
                if element_text:
                    max_page = int(element_text.strip())
                else:
                    break  # No text
            except Exception:
                if "a-disabled" in element["class"]:  # type: ignore
                    continue
                break

        return max_page

    def shutdown(self):
        try:
            self.br.close()
        except Exception:
            pass
        try:
            self.br.quit()
        except Exception:
            pass

    def get_params_string(self):
        return "?" + "&".join([f"{k}={quote_plus(v)}" for k, v in self.params])

    def register_param_item(self, key: str, value: Any):
        self.params.append((key, str(value)))

    def make_param_string(self):  # Usable
        self.params: List[Tuple[str, str]] = []

        item = self.category_info["category"]
        if item:
            self.register_param_item("i", item.value)

        item = self.sorting_method
        if item:
            self.register_param_item("s", item.value)

        item = self.make_search_options()
        if item:
            self.register_param_item("rh", item)

        item = self.keywords
        if item:
            self.register_param_item("k", item)

        return self.get_params_string()

    def set_sorting_options(self, sorting_method: Optional[SORTING]):  # Usable
        return sorting_method if sorting_method else SORTING.PRICE

    def set_rating_options(self, rating: int):  # Usable
        if rating <= 0:
            return None
        elif rating == 1:
            return RATING_FILTER.STARS_ONE
        elif rating == 2:
            return RATING_FILTER.STARS_TWO
        elif rating == 3:
            return RATING_FILTER.STARS_THREE
        else:
            return RATING_FILTER.STARS_FOUR

    def set_category_options(
        self, category, sub_category
    ) -> CategoryInfoType:  # Usable
        return {
            "category": category,
            "subcategory": sub_category,
        }

    def set_price_options(self, min, max) -> Tuple[float, float]:  # Usable
        return (min or 0, max or 0)

    def set_shipping_options(
        self,
        prime_national,
        prime_international,
        amazon_fulfilled,
        same_day_delivery,
        next_day_delivery,
        include_out_of_stock,
    ) -> DeliveryOptionsType:  # Usable

        prime_national = SHIPPING.SHIPPING_DOMESTIC if prime_national else None
        prime_international = (
            SHIPPING.SHIPPING_INTERNATIONAL if prime_international else None
        )
        amazon_fulfilled = SHIPPING.SHIPPING_FULFILLED if amazon_fulfilled else None
        same_day_delivery = SHIPPING.DELIVERY_SAME_DAY if same_day_delivery else None
        next_day_delivery = SHIPPING.DELIVERY_NEXT_DAY if next_day_delivery else None
        include_out_of_stock = (
            SHIPPING.ITEM_OUTOFSTOCK if include_out_of_stock else None
        )
        return {
            "domestic": prime_national,
            "international": prime_international,
            "verified": amazon_fulfilled,
            "same_day": same_day_delivery,
            "next_day": next_day_delivery,
            "oos": include_out_of_stock,
        }

    def get_shipping_info_string(self):
        shipping_info: List[SHIPPING] = []

        if self.shipping_information["domestic"]:
            shipping_info.append(self.shipping_information["domestic"])
        if self.shipping_information["international"]:
            shipping_info.append(self.shipping_information["international"])

        if shipping_info:
            return "|".join([str(s.value) for s in shipping_info])
        else:
            return None

    def register_rh_item(self, key: str, val: Any):
        self.rh_items.append((key, str(val)))

    def get_delivery_info_string(self):
        if self.shipping_information["same_day"]:
            return self.shipping_information["same_day"].value
        if self.shipping_information["next_day"]:
            return self.shipping_information["next_day"].value
        return None

    def _get_price_filter(self, price: float):
        return int(price * 100)

    def get_price_range_string(self):
        a, b = self.price_range
        a = self._get_price_filter(a) if a else ""
        b = self._get_price_filter(b) if b else ""

        return f"{a}-{b}" if (a or b) else None

    def get_rh_string(self):
        return ",".join([f"{k}:{v}" for k, v in self.rh_items])

    def make_search_options(self):
        self.rh_items: List[Tuple[str, str]] = []

        item = self.category_info["subcategory"]
        if item:
            self.register_rh_item("n", item.value)

        item = self.get_shipping_info_string()
        if item:
            self.register_rh_item("p_n_prime_domestic", item)

        item = self.shipping_information["verified"]
        if item:
            self.register_rh_item("p_n_fulfilled_by_amazon", item.value)

        item = self.get_delivery_info_string()
        if item:
            self.register_rh_item("p_90", item)

        item = self.shipping_information["oos"]
        if item:
            self.register_rh_item("p_n_availability", item.value)

        item = self.min_rating
        if item:
            self.register_rh_item("p_72", item.value)

        item = self.get_price_range_string()
        if item:
            self.register_rh_item("p_36", item)

        return self.get_rh_string()


obj = AmazonSearch(
    DEPARTMENT.COMPUTERS,
    CATEGORY.LAPTOPS,
    prime_national=False,
    prime_international=False,
    min_price=0,
    max_price=0,
    sorting_method=SORTING.PRICE,
    amazon_fulfilled=False,
    same_day_delivery=False,  # Mutually Exclusive v
    next_day_delivery=False,  # Mutually Exclusive ^
    include_out_of_stock=True,
    min_rating=0,
    keywords="",
)
obj.run()
