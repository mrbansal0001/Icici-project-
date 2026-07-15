import undetected_chromedriver as uc
import time

options = uc.ChromeOptions()
# options.add_argument('--headless')
options.add_argument('--no-sandbox')

try:
    driver = uc.Chrome(options=options, version_main=149)
    driver.get("https://www.ibo.org/programmes/find-an-ib-school/?SearchFields.Country=IN")
    time.sleep(15)
    with open("ibo_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved ibo_page.html")
except Exception as e:
    print(f"Error: {e}")
finally:
    try:
        driver.quit()
    except:
        pass
