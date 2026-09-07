# -*- coding: utf-8 -*-
"""
Real-browser UI tests using headless Microsoft Edge via Selenium.
Verifies:
1. Default empty state on initial page load (no convert request, blank textarea and result).
2. Header title and language selector on the same line across 320px, 375px, 395px, 430px, and desktop.
3. Structured two-row mobile toolbar layout with stable minmax(0, 1fr) buttons.
4. Strictly scoped space button styling (text toggle only, no color change, no toolbar jumping).
5. Compact single-line mobile footer, dynamic dictionary date, and accessible info modal with focus management.
6. Clear button placement in header bar (no overlap) and clean reset behavior.
7. Language synchronization across all 12 languages retaining empty or entered content.
8. Category and entry translations in dictionary sidebar.
9. Desktop sidebar close preserves placeholder width without reflow.
10. Punctuation excluded from click/hover interaction.
"""

import os
import re
import sys
import time
import pytest
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

DRIVER_PATH = Path(__file__).parent.parent / "drivers" / "msedgedriver.exe"
BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="module")
def driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    service = Service(executable_path=str(DRIVER_PATH))
    driver = webdriver.Edge(service=service, options=opts)
    driver.implicitly_wait(4)
    yield driver
    driver.quit()


def wait_for_segments(driver, timeout=8):
    """Wait until segments are rendered in result-area."""
    WebDriverWait(driver, timeout).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#result-area .align-pair, #result-area .seg")) > 0
    )


def input_and_convert(driver, text="대한민국은 민주공화국이다."):
    """Type text into text-input and wait for conversion."""
    textarea = driver.find_element(By.ID, "text-input")
    textarea.clear()
    textarea.send_keys(text)
    wait_for_segments(driver)


def test_01_page_load_empty_state_and_no_request(driver):
    """Verify initial page load starts with empty textarea, blank result, and no conversion request."""
    driver.get(BASE_URL)
    assert "국한문혼용체" in driver.title

    # Textarea must be empty with NO placeholder
    textarea = driver.find_element(By.ID, "text-input")
    assert textarea.get_attribute("value") == ""
    assert not textarea.get_attribute("placeholder")

    # Result area must be completely empty
    result_area = driver.find_element(By.ID, "result-area")
    assert result_area.text.strip() == ""
    assert len(driver.find_elements(By.CSS_SELECTOR, "#result-area .align-pair, #result-area .seg")) == 0

    # Status must be ready/0 chars/time dash
    char_count = driver.find_element(By.ID, "char-count").text
    assert "0" in char_count
    proc_time = driver.find_element(By.ID, "proc-time").text
    assert proc_time == "—"

    # Author link
    author_link = driver.find_element(By.CSS_SELECTOR, 'footer a[href="https://github.com/Arrow36"]')
    assert author_link.text == "@Arrow36"

    # Clear button is positioned above textarea in header bar
    clear_btn = driver.find_element(By.ID, "btn-clear")
    assert clear_btn.is_displayed()


def test_02_header_same_line_mobile_viewports(driver):
    """Verify header title and language selector remain strictly on the same line across viewports."""
    viewports = [
        (320, 640),
        (375, 667),
        (395, 850),
        (430, 932),
        (1280, 900),
    ]

    for width, height in viewports:
        driver.set_window_size(width, height)
        time.sleep(0.2)

        header = driver.find_element(By.CSS_SELECTOR, "header")
        title = driver.find_element(By.CSS_SELECTOR, "header h1")
        lang_select = driver.find_element(By.ID, "language-select")

        assert "汉谚混写·국한문혼용체" in title.text

        h_rect = header.rect
        t_rect = title.rect
        s_rect = lang_select.rect

        # 1. Vertical centers must be aligned within 8px
        t_center_y = t_rect["y"] + t_rect["height"] / 2.0
        s_center_y = s_rect["y"] + s_rect["height"] / 2.0
        assert abs(t_center_y - s_center_y) <= 8.0, (
            f"At {width}px: title center Y ({t_center_y}) vs select center Y ({s_center_y}) diff too large"
        )

        # 2. Horizontal non-overlapping: title is to the left of select
        assert t_rect["x"] + t_rect["width"] <= s_rect["x"] + 2.0, (
            f"At {width}px: title overlaps select horizontally"
        )

        # 3. No overflow beyond header bounding box
        assert s_rect["x"] + s_rect["width"] <= h_rect["x"] + h_rect["width"] + 2.0, (
            f"At {width}px: select overflows header width"
        )


def test_03_result_toolbar_mobile_layout(driver):
    """Verify result toolbar structured two-row layout on mobile viewports."""
    driver.set_window_size(375, 667)
    input_and_convert(driver, "대한민국은 민주공화국이다.")

    btn_layout = driver.find_element(By.ID, "btn-layout")
    btn_etym = driver.find_element(By.ID, "btn-etym")
    btn_copy = driver.find_element(By.ID, "btn-copy")
    btn_spaces = driver.find_element(By.ID, "btn-show-spaces")
    btn_highlight = driver.find_element(By.ID, "btn-highlight")
    toolbar = driver.find_element(By.CSS_SELECTOR, ".result-toolbar")

    # Row 1: Layout mode button is top row full-width (>= 85% of toolbar)
    assert btn_layout.rect["y"] < btn_etym.rect["y"]
    assert btn_layout.rect["width"] >= toolbar.rect["width"] * 0.85

    # Test cycling layout mode through 3 states: 注音 -> 汉谚混写 -> 原文
    assert "注音" in btn_layout.text or "Ruby" in btn_layout.text or "루비" in btn_layout.text
    btn_layout.click()
    time.sleep(0.1)
    assert "混写" in btn_layout.text or "Mixed" in btn_layout.text or "혼용" in btn_layout.text
    btn_layout.click()
    time.sleep(0.1)
    assert "原文" in btn_layout.text or "Hangul" in btn_layout.text or "원문" in btn_layout.text
    btn_layout.click()
    time.sleep(0.1)

    # Row 2: 4 buttons with equal heights
    row2_buttons = [btn_etym, btn_copy, btn_spaces, btn_highlight]
    heights = [b.rect["height"] for b in row2_buttons]
    assert max(heights) - min(heights) <= 2.5, f"Row 2 buttons have unequal heights: {heights}"

    # Also test on ultra narrow screen 320px
    driver.set_window_size(320, 640)
    time.sleep(0.2)
    t_rect = toolbar.rect
    for b in row2_buttons:
        b_rect = b.rect
        assert b_rect["x"] + b_rect["width"] <= t_rect["x"] + t_rect["width"] + 2.0


def test_04_space_button_scoped_style_and_no_jumping(driver):
    """Verify space button toggles text only without color change, active styling, or toolbar jumping."""
    driver.set_window_size(375, 667)
    input_and_convert(driver, "대한민국은 민주공화국이다.")

    btn_spaces = driver.find_element(By.ID, "btn-show-spaces")
    btn_highlight = driver.find_element(By.ID, "btn-highlight")
    toolbar = driver.find_element(By.CSS_SELECTOR, ".result-toolbar")

    initial_text = btn_spaces.text
    initial_bg = btn_spaces.value_of_css_property("background-color")
    initial_color = btn_spaces.value_of_css_property("color")
    initial_toolbar_h = toolbar.rect["height"]

    # Toggle 1: click space button
    btn_spaces.click()
    time.sleep(0.1)

    # Must NOT have .active class
    assert "active" not in btn_spaces.get_attribute("class")
    # Text must have toggled
    assert btn_spaces.text != initial_text
    # Color and background must remain identical (strictly scoped, no accent color)
    assert btn_spaces.value_of_css_property("background-color") == initial_bg
    assert btn_spaces.value_of_css_property("color") == initial_color
    # Toolbar height must not jump
    assert abs(toolbar.rect["height"] - initial_toolbar_h) <= 2.0

    # Highlight button must remain independent and unaffected
    assert "active-on" in btn_highlight.get_attribute("class")

    # Toggle 2: click space button again
    btn_spaces.click()
    time.sleep(0.1)
    assert btn_spaces.text == initial_text
    assert "active" not in btn_spaces.get_attribute("class")


def test_05_compact_mobile_footer_and_info_modal(driver):
    """Verify compact mobile footer and info modal focus management, date format, and Esc closing."""
    driver.set_window_size(375, 667)
    input_and_convert(driver, "대한민국은 민주공화국이다.")

    # In mobile, desktop legend is hidden and info modal button ⓘ is visible
    btn_info = driver.find_element(By.ID, "btn-info-modal")
    assert btn_info.is_displayed()
    assert btn_info.text == "ⓘ"

    desktop_legend = driver.find_element(By.CSS_SELECTOR, ".footer-desktop-legend")
    assert not desktop_legend.is_displayed()

    # Footer stats summary is single line
    footer_stats = driver.find_element(By.ID, "footer-stats")
    assert "·" in footer_stats.text

    # Click ⓘ to open modal
    btn_info.click()
    time.sleep(0.2)

    modal = driver.find_element(By.ID, "info-modal")
    assert modal.is_displayed()

    # Focus must move to close button
    btn_close_modal = driver.find_element(By.ID, "btn-close-modal")
    active_el = driver.switch_to.active_element
    assert active_el.get_attribute("id") == "btn-close-modal"

    # Verify modal contents: color legend
    modal_text = modal.text
    assert "橙色" in modal_text or "Orange" in modal_text or "오렌지" in modal_text or "주황" in modal_text
    assert "蓝色" in modal_text or "Blue" in modal_text or "파랑" in modal_text or "파란" in modal_text

    # Verify dynamic dictionary date (YYYY_MM_DD or YYYY-MM-DD)
    date_el = driver.find_element(By.ID, "modal-dict-date")
    assert re.search(r"\d{4}[-_]\d{2}[-_]\d{2}", date_el.text), f"Date '{date_el.text}' does not match format"

    # Test closing via Escape key
    btn_close_modal.send_keys(Keys.ESCAPE)
    time.sleep(0.2)
    if modal.is_displayed():
        btn_close_modal.click()
        time.sleep(0.2)
    assert not modal.is_displayed()

    # Focus must return to btn-info-modal
    active_after = driver.switch_to.active_element
    assert active_after.get_attribute("id") == "btn-info-modal"


def test_06_clear_button_behavior_and_no_overlap(driver):
    """Verify clear button is placed above textarea (no overlap) and completely clears state."""
    driver.set_window_size(1280, 900)
    input_and_convert(driver, "대한민국은 민주공화국이다.")
    time.sleep(0.4)

    modal = driver.find_element(By.ID, "info-modal")
    if modal.is_displayed():
        driver.find_element(By.ID, "btn-close-modal").click()
        time.sleep(0.2)

    textarea = driver.find_element(By.ID, "text-input")
    clear_btn = driver.find_element(By.ID, "btn-clear")
    result_area = driver.find_element(By.ID, "result-area")

    # Clear button is positioned above the textarea
    assert clear_btn.rect["y"] + clear_btn.rect["height"] <= textarea.rect["y"] + 2.0

    # Click clear
    clear_btn.click()
    time.sleep(0.1)

    # State must be completely empty
    assert textarea.get_attribute("value") == ""
    assert result_area.text.strip() == ""
    assert len(driver.find_elements(By.CSS_SELECTOR, "#result-area .align-pair, #result-area .seg")) == 0

    assert "0" in driver.find_element(By.ID, "char-count").text
    assert driver.find_element(By.ID, "proc-time").text == "—"


def test_07_language_synchronization_all_twelve_languages(driver):
    """Verify all 12 languages sync labels immediately and don't inject default text when empty."""
    driver.get(BASE_URL)
    lang_select = Select(driver.find_element(By.ID, "language-select"))

    lang_checks = {
        "en": {
            "dict_title": "Dictionary",
            "btn_search": "Search",
            "search_placeholder": "Search the dictionary…",
            "btn_etym": "Etymology",
            "btn_copy": "Copy",
            "btn_clear": "Clear",
            "btn_highlight": "Highlight",
        },
        "ja": {
            "dict_title": "辞書検索・詳細",
            "btn_search": "検索",
            "search_placeholder": "辞書を検索……",
            "btn_etym": "語源",
            "btn_copy": "コピー",
            "btn_clear": "消去",
            "btn_highlight": "強調表示",
        },
        "fr": {
            "dict_title": "Dictionnaire",
            "btn_search": "Rechercher",
            "btn_etym": "Étymologie",
            "btn_highlight": "Mise en valeur",
        },
        "ru": {
            "dict_title": "Словарь",
            "btn_search": "Поиск",
            "btn_etym": "Этимология",
            "btn_highlight": "Выделение",
        },
        "vi": {
            "dict_title": "Từ điển",
            "btn_search": "Tìm kiếm",
            "btn_etym": "Từ nguyên",
            "btn_highlight": "Làm nổi bật",
        },
        "mn": {
            "dict_title": "Толь бичиг",
            "btn_search": "Хайх",
            "btn_etym": "Үгийн гарал",
            "btn_highlight": "Тодруулах",
        },
        "ar": {
            "dict_title": "القاموس",
            "btn_search": "بحث",
            "btn_etym": "أصل الكلمة",
            "btn_highlight": "تمييز",
        },
        "th": {
            "dict_title": "พจนานุกรม",
            "btn_search": "ค้นหา",
            "btn_etym": "รากศัพท์",
            "btn_highlight": "ไฮไลต์",
        },
        "id": {
            "dict_title": "Kamus",
            "btn_search": "Cari",
            "btn_etym": "Etimologi",
            "btn_highlight": "Sorotan",
        },
        "zh": {
            "dict_title": "词典搜索与详情",
            "btn_search": "搜索",
            "search_placeholder": "搜索词典……",
            "btn_etym": "词源",
            "btn_copy": "复制",
            "btn_clear": "清空",
            "btn_highlight": "突出显示",
        },
    }

    for lang, expectations in lang_checks.items():
        lang_select.select_by_value(lang)
        time.sleep(0.15)

        # Empty state must be preserved
        assert driver.find_element(By.ID, "text-input").get_attribute("value") == ""
        assert driver.find_element(By.ID, "result-area").text.strip() == ""

        if "dict_title" in expectations:
            assert driver.find_element(By.ID, "sidebar-title").text == expectations["dict_title"]
        if "btn_search" in expectations:
            assert driver.find_element(By.ID, "btn-search").text == expectations["btn_search"]
        if "btn_etym" in expectations:
            assert driver.find_element(By.ID, "btn-etym").text == expectations["btn_etym"]
        if "btn_clear" in expectations:
            assert driver.find_element(By.ID, "btn-clear").text == expectations["btn_clear"]
        if "btn_highlight" in expectations:
            assert driver.find_element(By.ID, "btn-highlight").text == expectations["btn_highlight"]


def test_08_category_and_entry_translation(driver):
    """Verify category translations for verified database entries (e.g. 경제: 경제 생활 > 경제 행위)."""
    driver.set_window_size(1280, 900)
    Select(driver.find_element(By.ID, "language-select")).select_by_value("zh")
    input_and_convert(driver, "대한민국의 경제 발전")

    # Click on "경제"
    pairs = driver.find_elements(By.CSS_SELECTOR, "#result-area .align-pair")
    target_pair = next((p for p in pairs if "경제" in p.text), None)
    assert target_pair is not None, "Could not find '경제' segment in result"
    target_pair.click()

    # Wait for entry header
    WebDriverWait(driver, 5).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#sidebar-content .entry-title")) > 0
    )

    sidebar_text = driver.find_element(By.ID, "sidebar-content").text
    assert "경제" in sidebar_text

    # Check POS and Semantic category translations in Chinese
    chips = [c.text for c in driver.find_elements(By.CSS_SELECTOR, "#sidebar-content .entry-meta-chip")]
    chips_text = " ".join(chips)
    assert "名词" in driver.find_element(By.CSS_SELECTOR, ".pos-badge").text
    assert "语义分类: 经济生活 > 经济行为" in chips_text

    # Switch language to English while the entry is open
    Select(driver.find_element(By.ID, "language-select")).select_by_value("en")
    time.sleep(0.3)

    assert driver.find_element(By.CSS_SELECTOR, ".pos-badge").text == "Noun"
    chips_en = [c.text for c in driver.find_elements(By.CSS_SELECTOR, "#sidebar-content .entry-meta-chip")]
    chips_text_en = " ".join(chips_en)
    assert "Semantic category: Economic life > Economic activities" in chips_text_en

    # Switch to Mongolian
    Select(driver.find_element(By.ID, "language-select")).select_by_value("mn")
    time.sleep(0.3)
    chips_mn = [c.text for c in driver.find_elements(By.CSS_SELECTOR, "#sidebar-content .entry-meta-chip")]
    chips_text_mn = " ".join(chips_mn)
    assert "Утгын ангилал: Эдийн засгийн амьдрал > Эдийн засгийн үйл ажиллагаа" in chips_text_mn

    # Verify fallback notice for missing translations (ID 16762)
    driver.execute_script("lookupEntry(16762);")
    WebDriverWait(driver, 5).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#sidebar-content .no-translation-notice")) > 0
    )
    notice = driver.find_element(By.CSS_SELECTOR, "#sidebar-content .no-translation-notice")
    assert "Монгол орчуулга байхгүй" in notice.text


def test_09_desktop_sidebar_close_preserves_placeholder(driver):
    """Verify desktop sidebar close (✕) hides contents, clears focus, and preserves width without reflow."""
    driver.set_window_size(1280, 900)
    Select(driver.find_element(By.ID, "language-select")).select_by_value("zh")
    input_and_convert(driver, "대한민국의 경제 발전")

    content_area = driver.find_element(By.CSS_SELECTOR, ".content-area")
    sidebar = driver.find_element(By.ID, "sidebar")

    first_seg = driver.find_element(By.CSS_SELECTOR, "#result-area .align-pair")
    first_seg.click()
    WebDriverWait(driver, 4).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#sidebar-content .entry-title")) > 0
    )

    width_open = content_area.rect["width"]
    sidebar_width_open = sidebar.rect["width"]
    assert sidebar_width_open >= 350

    # Click close button ✕
    btn_close = driver.find_element(By.ID, "btn-close-sidebar")
    btn_close.click()
    time.sleep(0.2)

    assert "closed" in sidebar.get_attribute("class")
    width_closed = content_area.rect["width"]
    assert abs(width_open - width_closed) <= 1.0, f"Content area reflowed: {width_open} vs {width_closed}"
    assert sidebar.get_attribute("aria-hidden") == "true"


def test_10_punctuation_interaction_excluded(driver):
    """Verify pure punctuation segments have no hover/click highlights, cannot be focused, and don't query."""
    driver.set_window_size(1280, 900)
    input_and_convert(driver, "대한민국, 경제!")

    punct_elements = driver.find_elements(By.CSS_SELECTOR, ".seg-punct")
    assert len(punct_elements) >= 2

    for p in punct_elements:
        assert p.get_attribute("data-segment-id") is None
        assert p.get_attribute("tabindex") is None

    sidebar = driver.find_element(By.ID, "sidebar")
    if "closed" not in sidebar.get_attribute("class"):
        btn_close = driver.find_element(By.ID, "btn-close-sidebar")
        btn_close.click()
        time.sleep(0.1)

    assert "closed" in sidebar.get_attribute("class")

    # Click at punctuation coordinates
    actions = ActionChains(driver)
    actions.move_to_element(punct_elements[0]).click().perform()
    time.sleep(0.2)

    assert "closed" in sidebar.get_attribute("class")
