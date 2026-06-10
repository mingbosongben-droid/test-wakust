import os
import math
import re
import sys
import random
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright, TimeoutError

# ---------------------------------------------------------
# 設定エリア
# ---------------------------------------------------------
USER_ID = os.environ.get("SITE_USER_ID")
PASSWORD = os.environ.get("SITE_PASSWORD")

# エリア・カテゴリ定義
CATEGORY_MAP = {
    "北海道": "16", "東北": "8475", "北関東": "8421",
    "埼玉県": "2442", "千葉県": "2441", "東京都": "4",
    "池袋": "24474", "新宿": "24476", "多摩": "24624",
    "神奈川県": "1245", "イケメン": "35084", "静岡県": "24621",
    "甲信越北陸": "6722", "愛知県": "19", "栄": "24623",
    "岐阜三重": "24622", "大阪府": "331", "日本橋": "24620",
    "兵庫県": "24533", "関西": "18", "中国": "955",
    "四国": "24619", "福岡県": "2348", "九州": "8401",
    "海外": "10750",
    "ノウハウ(ネット)": "6898",
    "ノウハウ(リアル)": "6897",
    "美容健康": "9587", "R18小説": "22878",
    "生成AI動画像(審査中)": "30765", "ラウンジ": "1315"
}

# デフォルト設定
DEFAULT_TARGETS = list(CATEGORY_MAP.keys())
env_targets = os.environ.get("TARGET_AREAS")
if env_targets:
    TARGET_LIST = [x.strip() for x in env_targets.split(",") if x.strip()]
else:
    TARGET_LIST = DEFAULT_TARGETS

TARGET_URL = "https://wakust.com/login/"
POST_LIST_URL = "https://wakust.com/mypage/?post_list"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_today_jst():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST).strftime('%Y-%m-%d')

def human_wait(page, min_ms=800, max_ms=2000):
    ms = random.randint(min_ms, max_ms)
    page.wait_for_timeout(ms)

def run():
    with sync_playwright() as p:
        today_str = get_today_jst()
        print(f"--- 自動処理開始 ---")
        print(f"実行日(JST): {today_str}")
        print(f"巡回対象: {len(TARGET_LIST)} エリア")

        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP", timezone_id="Asia/Tokyo"
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        print("\n=== 1. ログイン処理 ===")
        try:
            page.goto(TARGET_URL)
            page.wait_for_load_state("domcontentloaded")
            human_wait(page, 1500, 2500)
            try:
                if page.is_visible('#age-verify-yes'):
                    page.click('#age-verify-yes')
                    human_wait(page, 500, 1000)
            except: pass

            page.fill('input[name="login_email"]', USER_ID)
            human_wait(page, 300, 800)
            page.fill('input[name="login_password"]', PASSWORD)
            human_wait(page, 300, 1000)

            try:
                page.evaluate("var e = document.getElementById('age-verification-modal'); if(e) e.remove();")
            except: pass

            with page.expect_navigation(wait_until="domcontentloaded"):
                page.click('button.login_submit', force=True)
            print("-> ログイン成功")

        except Exception as e:
            print(f"FATAL ERROR: ログイン失敗\n{e}")
            sys.exit(1)

        human_wait(page, 1500, 3000)

        for idx, target_name in enumerate(TARGET_LIST):
            cat_id = CATEGORY_MAP.get(target_name)
            print(f"\n[{idx+1}/{len(TARGET_LIST)}] カテゴリ: {target_name} (ID: {cat_id})")
            print("-" * 40)
            if not cat_id: continue

            try:
                if "post_list" not in page.url:
                    try:
                        page.click('#m_5 a', timeout=3000)
                        page.wait_for_load_state("domcontentloaded")
                    except:
                        page.goto(POST_LIST_URL)
                        page.wait_for_load_state("domcontentloaded")
                    human_wait(page, 1000, 2000)
                if "post_list" not in page.url:
                    page.goto(POST_LIST_URL)
                    human_wait(page, 1000, 2000)

                page.select_option('select[name="cat"]', cat_id)
                human_wait(page, 300, 800)
                with page.expect_navigation(wait_until="domcontentloaded"):
                    page.click('#button-addon2')
                human_wait(page, 1500, 3000)

                count_element = page.locator('div.float-start > div').first
                if not count_element.is_visible(): continue
                count_text = count_element.inner_text()
                match = re.search(r'(\d+)', count_text)
                total_items = int(match.group(1)) if match else 0
                if total_items == 0: continue

                if total_items > 20:
                    page_num = math.ceil(total_items / 20)
                    print(f"-> {total_items}件 / 最終ページ({page_num}P)へ移動")
                    current_url = page.url
                    sep = "&" if "?" in current_url else "?"
                    page.goto(f"{current_url}{sep}cp={page_num}")
                    page.wait_for_load_state("domcontentloaded")
                    human_wait(page, 1500, 3000)
                else:
                    print("-> 1ページ目で探索")

                rows = page.locator('table.table tbody tr')
                page.wait_for_timeout(1000)
                row_count = rows.count()
                target_found = False

                for i in range(row_count - 1, -1, -1):
                    try:
                        row = rows.nth(i)
                        sel_locator = row.locator('.select_post_sol')
                        sel_locator.wait_for(state="attached", timeout=3000)
                        status_val = sel_locator.input_value()
                        title_txt = row.locator('.td_2').inner_text()

                        is_match = False
                        if status_val == "0":
                            if target_name == "ノウハウ(リアル)":
                                is_match = True
                            else:
                                if "出勤" in title_txt: is_match = True
                                elif "まとめ" in title_txt: is_match = True
                                elif re.search(r'\d{1,2}選', title_txt): is_match = True
                                elif re.search(r'\d{1,2}名', title_txt): is_match = True

                        if is_match:
                            print(f"-> ★ 再投稿候補: {title_txt[:15]}...")
                            human_wait(page, 500, 1000)
                            with page.expect_navigation(wait_until="domcontentloaded"):
                                row.locator('.td_6 a').click()
                            target_found = True
                            break
                    except: continue

                if not target_found:
                    print("-> 候補記事なし")
                    continue

                print("-> 編集画面: 再投稿処理...")
                human_wait(page, 1000, 2000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                human_wait(page, 500, 1000)

                if page.is_visible('#repost'):
                    page.click('#repost', force=True)
                    print("-> [Action] #repost クリック")
                    page.wait_for_timeout(1500)
                    if page.is_visible('#error_text'):
                        print(f"-> 🛑 エラー検知(スキップ): {page.locator('#error_text').inner_text()}")
                        page.goto(POST_LIST_URL)
                        page.wait_for_load_state("domcontentloaded")
                        continue
                else:
                    print("-> ⚠️ #repostボタンなし")

                human_wait(page, 500, 1500)
                if page.is_visible('#submit_edit_s'):
                    page.click('#submit_edit_s', force=True)
                    print("-> [Action] 確認ボタン押下")
                    try: page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except: pass
                    human_wait(page, 1500, 3000)

                if page.is_visible('#submit_edit'):
                    print("-> [Action] 確定ボタン押下")
                    try:
                        with page.expect_navigation(wait_until="domcontentloaded", timeout=120000):
                            page.click('#submit_edit', force=True)
                        print("-> [OK] 再投稿完了")
                        page.wait_for_timeout(10000)
                    except TimeoutError:
                        print("-> ⚠️ 遷移タイムアウト(完了とみなす)")
                        page.wait_for_timeout(10000)
                        try: page.goto(POST_LIST_URL)
                        except: pass
                else:
                    print("-> ⚠️ 確定ボタンなし")
                    human_wait(page, 2000, 4000)

            except Exception as e:
                print(f"-> ⚠️ エラー発生: {e}")
                try: page.goto(POST_LIST_URL)
                except: pass
                continue

if __name__ == "__main__":
    run()
