import requests
import xmltodict
import json

def fetch_safety_law():
    print("🚀 '산업안전보건기준에 관한 규칙' 데이터 불러오는 중...")
    
    url = "https://www.law.go.kr/DRF/lawService.do"
    
    # 💡 [중요] "여기에_발급받은_아이디_입력" 부분을 지우고 새로 얻으신 API 아이디를 넣으세요!
    params = {
        "OC": "s-black723",  
        "target": "law",
        "query": "산업안전보건기준에 관한 규칙",
        "type": "XML"
    }

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        law_dict = xmltodict.parse(response.content)
        
        # 정상적으로 데이터를 받았는지 구조 확인
        if '법령' not in law_dict:
            print("\n❌ 오류 발생: API 키가 잘못되었거나 접근이 차단되었습니다.")
            print(response.text[:500])
            return None
            
        # 법령 안에서 실제 조문들이 담긴 리스트 추출
        articles = law_dict['법령']['조문']['조문단위']
        
        print(f"\n✅ 성공적으로 법령 데이터를 불러왔습니다!")
        print(f"📊 총 조문 개수: {len(articles)}개")
        print("-" * 50)
        
        # 맛보기로 1조부터 3조까지 화면에 출력해서 확인해보기
        for article in articles[:3]:
            article_num = article.get('@조문번호', '번호없음')
            article_title = article.get('조문제목', '제목없음')
            article_content = article.get('조문내용', '').strip()
            
            print(f"📌 [제 {article_num}조] {article_title}")
            print(f"{article_content}")
            print("-" * 50)
            
        return articles
    else:
        print(f"❌ API 통신 실패: 상태 코드 {response.status_code}")
        return None

if __name__ == "__main__":
    law_data = fetch_safety_law()
    
    # 정상적으로 데이터를 불러왔다면 파일로 안전하게 저장
    if law_data:
        with open("safety_law.json", "w", encoding="utf-8") as f:
            json.dump(law_data, f, ensure_ascii=False, indent=2)
            print("💾 로컬 폴더에 'safety_law.json' 파일로 구조화 데이터 저장 완료!")