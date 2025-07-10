import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
from playwright.async_api import async_playwright

# .env ფაილიდან გარემოს ცვლადების ჩატვირთვა
load_dotenv()

# ლოგ ფაილის სახელი და მდებარეობა
log_filename = "speedface_log"
script_path = os.path.dirname(os.path.realpath(__file__))
log_file_path = os.path.join(script_path, log_filename)

# ფუნქცია: ბეჭდავს და ინახავს შეტყობინებებს ლოგ ფაილში
def print_and_log(message):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file_path, "a") as log_file:
        log_file.write(f"[{current_time}] {message}\n")

# გარემოს ცვლადებიდან მონაცემთა ბაზის პარამეტრების მიღება
mysql_ip = os.getenv("MYSQL_HOST")
mysql_user = os.getenv("MYSQL_USER")
mysql_pass = os.getenv("MYSQL_PASS")
mysql_db = os.getenv("MYSQL_DB")
mysql_table = os.getenv("MYSQL_TABLE")
turnstile_url = os.getenv("TURNSTILE_URL")

# ასინქრონული ფუნქცია: მონაცემების წამოღება ვებსაიტიდან Playwright-ის გამოყენებით
async def playwright_speedface():
    data_list = []
    try:
        async with async_playwright() as p:
            # ბრაუზერის გაშვება headless რეჟიმში
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # საიტის გახსნა
            await page.goto(turnstile_url)
            await page.wait_for_timeout(5000)  # დაველოდოთ 5 წამი

            # მომხმარებლის სახელის და პაროლის შევსება
            await page.fill("#username", "speedface")
            await page.fill("#password", "Speedface@2024")
            await page.click("#test")  # შესვლის ღილაკზე დაჭერა
            await page.wait_for_timeout(5000)

            # ანგარიშის მენიუზე დაჭერა
            await page.click("#AccMenu")
            await page.wait_for_timeout(5000)

            # რეპორტების სექციაზე გადასვლა
            await page.click("xpath=//img[@src='public/images/menuTree/comm_reports.png']")
            await page.wait_for_timeout(5000)

            # დღევანდელი მოვლენების ნახვა
            await page.click("xpath=//span[text()='Events From Today']")
            await page.wait_for_timeout(5000)

            # ცხრილის მოძებნა
            tables = await page.query_selector_all(".objbox")
            if not tables:
                print_and_log("ცხრილში მონაცემები ვერ მოიძებნა.")
                return []

            first_table = tables[0]
            rows = await first_table.query_selector_all("tr")

            # ცხრილის თითოეული მწკრივის დამუშავება
            for row in rows:
                cols = await row.query_selector_all("td")
                if len(cols) > 7:
                    col_7_text = await cols[7].inner_text()
                    if not col_7_text.strip():
                        continue  # გამოტოვება ცარიელი მნიშვნელობების შემთხვევაში

                    col_1_text = await cols[1].inner_text()
                    col_3_text = await cols[3].inner_text()

                    # შესვლის/გასვლის სტატუსის ამოცნობა
                    in_out_state = 0 if col_3_text.strip().lower() == "chek inn" else 1 if col_3_text.strip().lower() == "chek out" else None
                    if in_out_state is not None:
                        data_list.append([col_1_text.strip(), col_7_text.strip(), in_out_state])

            # ბრაუზერის დახურვა
            await browser.close()
            return data_list

    except Exception as e:
        print_and_log(f"შეცდომა მოხდა: {str(e)}")
        return []

# ძირითადი ფუნქცია: მონაცემების მიღება და MySQL-ში შენახვა
async def main():
    data_list = await playwright_speedface()

    if not data_list:
        return  # თუ ცარიელია, არაფერს ვაკეთებთ

    try:
        # MySQL მონაცემთა ბაზასთან დაკავშირება
        db = mysql.connector.connect(
            host=mysql_ip,
            user=mysql_user,
            password=mysql_pass,
            database=mysql_db
        )
        cursor = db.cursor()

        # თითოეული ჩანაწერის შენახვა ბაზაში
        for data in data_list:
            insert_value = (
                f"INSERT IGNORE INTO `{mysql_table}` (date_time, card_number, in_out_state) "
                f"VALUES ('{data[0]}', '{data[1]}', {data[2]}) "
                f"ON DUPLICATE KEY UPDATE id=id"
            )
            cursor.execute(insert_value)
            db.commit()

    except mysql.connector.Error as e:
        print_and_log("MySQL-თან დაკავშირების შეცდომა: {}".format(e))

    except Exception as e:
        print_and_log("შეცდომა მონაცემების შენახვისას: {}".format(e))

    finally:
        # მონაცემთა ბაზის კავშირის დახურვა
        if 'db' in locals():
            db.close()

# სკრიპტის გაშვების წერტილი
if __name__ == "__main__":
    asyncio.run(main())
