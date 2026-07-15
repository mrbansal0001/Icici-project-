import undetected_chromedriver as uc
import time

options = uc.ChromeOptions()
options.add_argument('--headless')

try:
    driver = uc.Chrome(options=options, version_main=149)
    driver.get("https://saras.cbse.gov.in/saras/AffiliatedList/ListOfSchdirReport")
    time.sleep(10)
    with open("cbse_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved cbse_page.html")
except Exception as e:
    print(f"Error: {e}")
finally:
    try:
        driver.quit()
    except:
        pass
