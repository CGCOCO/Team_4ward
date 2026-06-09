import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "kosha_pdfs")

TARGET_INDUSTRIES = {
    "manufacturing": "https://portal.kosha.or.kr/archive/disaster-case/accident-case/acccase-industry/manufac-industry",
    "construction": "https://portal.kosha.or.kr/archive/disaster-case/accident-case/acccase-industry/construc-industry",
    "service": "https://portal.kosha.or.kr/archive/disaster-case/accident-case/acccase-industry/ser-industry"
}

def setup_driver(download_path):
    if not os.path.exists(download_path):
        os.makedirs(download_path)
        
    chrome_options = Options()
    
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1 
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def crawl_kosha_pdfs():
    # 딱 1페이지부터 10페이지까지만 정의 (화살표 절대 안 누름)
    target_pages = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    for industry, url in TARGET_INDUSTRIES.items():
        print(f"\n🚀 [{industry}] 크롤링 시작...")
        industry_dir = os.path.join(DOWNLOAD_DIR, industry)
        driver = setup_driver(industry_dir)
        
        try:
            driver.get(url)
            downloaded_count = 0
            
            for page_num in target_pages:
                print(f"--- {page_num}페이지 수집 시작 (누적 다운로드: {downloaded_count}개) ---")
                
                wait = WebDriverWait(driver, 10)
                
                # 1. 페이지 로딩 후 다운로드 버튼들 뜰 때까지 대기 및 수집
                download_buttons = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.tboard_icon_download"))
                )
                
                # 페이지 전환 완료 확인용 첫 글 제목 기억
                try:
                    first_article_title = driver.find_element(By.CSS_SELECTOR, "table tbody tr td.subject, table tbody tr td a").text
                except:
                    first_article_title = ""

                # 2. 현재 페이지 10개 다운로드 수행
                for btn in download_buttons:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        downloaded_count += 1
                        time.sleep(1.2)
                    except Exception as e:
                        print(f"다운로드 클릭 실패 (스킵): {e}")
                
                # 10페이지 다운로드가 끝났다면 다음 페이지 버튼을 찾지 않고 즉시 루프 종료
                if page_num == 10:
                    break
                    
                # 3. [수정] 화살표 로직을 완전히 삭제하고 다음 숫자 버튼만 정확히 타겟팅
                next_page_num = page_num + 1
                try:
                    # KOSHA 사이트의 페이지네이션 내 텍스트가 정확히 다음 숫자인 <button> 요소를 타겟
                    # 예: 1페이지 수집 끝났으면 텍스트가 '2'인 버튼을 강제 지정
                    next_page_button = driver.find_element(
                        By.XPATH, f"//div[contains(@class, 'pagination')]//button[text()='{next_page_num}']"
                    )
                    
                    # 자바스크립트로 해당 숫자 버튼 클릭
                    driver.execute_script("arguments[0].click();", next_page_button)
                    
                    # 4. 페이지가 실제로 넘어갔는지 제목 변화 체크 대기
                    if first_article_title:
                        start_time = time.time()
                        while True:
                            try:
                                current_title = driver.find_element(By.CSS_SELECTOR, "table tbody tr td.subject, table tbody tr td a").text
                                if current_title != first_article_title:
                                    break
                            except:
                                pass
                            if time.time() - start_time > 8:
                                break
                            time.sleep(0.5)
                                
                    time.sleep(1.5) # 안정적인 다음 페이지 렌더링 대기
                    
                except Exception as e:
                    print(f"❌ {next_page_num}번 숫자 버튼을 찾는 데 실패했습니다. 에러: {e}")
                    break
                    
        finally:
            time.sleep(5)
            driver.quit()

if __name__ == "__main__":
    crawl_kosha_pdfs() 
    print("\n✅ 모든 카테고리 1~10페이지 정주행 완료!")