import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import json
import html as html_lib
import re

class ST11Scraper:
    def __init__(self, headless=True):
        chrome_options = Options()
        
        # Render 환경 감지
        if os.getenv('RENDER'):
            # Render 클라우드 환경
            chrome_options.binary_location = '/usr/bin/chromium'
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # 로컬 환경
            if headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
    
    def search_products(self, keyword, max_items=50):
        """11번가에서 상품 검색"""
        search_url = f"https://search.11st.co.kr/Search.tmall?kwd={keyword}"
        
        try:
            print(f"🔍 '{keyword}' 검색 중...")
            self.driver.get(search_url)
            
            print("   페이지 로딩 대기 중...")
            time.sleep(5)
            
            # 페이지 맨 아래까지 스크롤
            print("   페이지 스크롤 중...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            scroll_count = 0
            max_scrolls = 10
            
            while scroll_count < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    print(f"   더 이상 스크롤할 내용 없음")
                    break
                
                last_height = new_height
                scroll_count += 1
                print(f"   스크롤 {scroll_count}회...")
            
            products = []
            product_links = self.driver.find_elements(By.CSS_SELECTOR, "a.c-card-item__anchor")
            
            print(f"   발견된 상품 링크: {len(product_links)}개")
            
            for link_elem in product_links[:max_items]:
                try:
                    product = self._parse_product_link(link_elem)
                    if product:
                        products.append(product)
                except:
                    continue
            
            print(f"   ✅ {len(products)}개 상품 수집 완료")
            return products
            
        except Exception as e:
            print(f"   ❌ 검색 오류: {e}")
            return []
    
    def _parse_product_link(self, link_elem):
        """a 태그에서 상품 정보 추출"""
        try:
            log_body = link_elem.get_attribute('data-log-body')
            if not log_body:
                return None
            
            log_body = html_lib.unescape(log_body)
            data = json.loads(log_body)
            
            content_no = data.get('content_no', '')
            if not content_no:
                return None
            
            product_url = f"https://www.11st.co.kr/products/{content_no}"
            
            price = int(data.get('last_discount_price', 0))
            if price == 0:
                return None
            
            try:
                name_elem = link_elem.find_element(By.CSS_SELECTOR, "span.sr-only")
                name = name_elem.text.strip()
            except:
                snippet = data.get('snippet_object', {})
                name = snippet.get('advert', '') or snippet.get('11talk', '') or f"상품번호 {content_no}"
            
            if not name or len(name) < 2:
                return None
            
            snippet = data.get('snippet_object', {})
            delivery = snippet.get('delivery_price', '배송비 확인필요')
            is_ad = data.get('ad_yn', 'N') == 'Y'
            
            quantity = self._extract_quantity(name)
            unit_price = price / quantity if quantity > 1 else price
            
            return {
                'name': name,
                'price': price,
                'unit_price': unit_price,
                'quantity': quantity,
                'link': product_url,
                'delivery': delivery,
                'is_ad': is_ad,
                'rating': None,
                'review_count': None,
                'seller_satisfaction': None,
                'seller_response': None,
                'seller_sales': None
            }
            
        except:
            return None
    
    def _extract_quantity(self, name):
        """상품명에서 묶음 개수 추출"""
        name_lower = name.lower()
        
        patterns = [
            r'(\d+)개', r'(\d+)입', r'(\d+)팩', r'(\d+)박스',
            r'(\d+)묶음', r'(\d+)병', r'(\d+)캔', r'(\d+)ea',
            r'(\d+)p', r'x\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name_lower)
            if match:
                try:
                    quantity = int(match.group(1))
                    if 1 < quantity < 1000:
                        return quantity
                except:
                    pass
        
        return 1
    
    def fetch_product_details(self, products, max_count=20):
        """상품 상세 페이지에서 별점, 리뷰, 판매자 정보 가져오기"""
        print(f"\n⭐ 상위 {max_count}개 상품의 상세 정보 수집 중...")
        
        for idx, product in enumerate(products[:max_count], 1):
            try:
                print(f"   {idx}/{max_count}: {product['name'][:40]}...")
                
                self.driver.get(product['link'])
                time.sleep(2)
                
                # 1. 메타 태그에서 별점/리뷰 추출
                try:
                    meta_desc = self.driver.find_element(By.XPATH, "//meta[@name='description']")
                    content = meta_desc.get_attribute('content')
                    
                    rating_match = re.search(r'평점:\s*(\d+\.?\d*)', content)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:
                            product['rating'] = rating
                    
                    review_match = re.search(r'리뷰수:\s*(\d+)', content)
                    if review_match:
                        product['review_count'] = int(review_match.group(1))
                except:
                    pass
                
                # 2. HTML에서 별점/리뷰 추출 (백업)
                if not product.get('rating'):
                    try:
                        rating_elem = self.driver.find_element(By.ID, "prdReviewStar")
                        rating_text = rating_elem.text
                        rating_match = re.search(r'(\d+\.?\d+)개', rating_text)
                        if rating_match:
                            rating = float(rating_match.group(1))
                            if 0 <= rating <= 5:
                                product['rating'] = rating
                    except:
                        pass
                
                if not product.get('review_count'):
                    try:
                        review_elem = self.driver.find_element(By.CSS_SELECTOR, "strong.text_num")
                        review_text = review_elem.text.strip().replace(',', '')
                        product['review_count'] = int(review_text)
                    except:
                        pass
                
                # 3. 판매자 정보 추출
                try:
                    seller_info = self.driver.find_elements(By.CSS_SELECTOR, "dl.info_cont dt")
                    for dt in seller_info:
                        if "판매자만족" in dt.text:
                            dd = dt.find_element(By.XPATH, "./following-sibling::dd")
                            product['seller_satisfaction'] = dd.text.strip()
                        elif "응답률" in dt.text:
                            dd = dt.find_element(By.XPATH, "./following-sibling::dd")
                            product['seller_response'] = dd.text.strip()
                        elif "판매량" in dt.text:
                            dd = dt.find_element(By.XPATH, "./following-sibling::dd")
                            try:
                                score_elem = dd.find_element(By.CSS_SELECTOR, "em[class*='score']")
                                score_class = score_elem.get_attribute('class')
                                score_match = re.search(r'score(\d+)', score_class)
                                if score_match:
                                    product['seller_sales'] = f"{score_match.group(1)}/5"
                            except:
                                product['seller_sales'] = dd.text.strip()
                except:
                    pass
                
                # 결과 출력
                info_parts = []
                if product.get('rating'):
                    info_parts.append(f"별점: {product['rating']}")
                if product.get('review_count'):
                    info_parts.append(f"리뷰: {product['review_count']}개")
                if product.get('seller_satisfaction'):
                    info_parts.append(f"만족: {product['seller_satisfaction']}")
                if product.get('seller_response'):
                    info_parts.append(f"응답: {product['seller_response']}")
                if product.get('seller_sales'):
                    info_parts.append(f"판매: {product['seller_sales']}")
                
                if info_parts:
                    print(f"      ✅ {', '.join(info_parts)}")
                else:
                    print(f"      ⚠️  상세 정보 없음")
                    
            except Exception as e:
                print(f"      ⚠️  오류: {str(e)[:50]}")
                continue
        
        print(f"   ✅ 상세 정보 수집 완료\n")
        return products
    
    def sort_by_price(self, products, ascending=True, by_unit=False):
        """가격순 정렬"""
        sort_key = 'unit_price' if by_unit else 'price'
        return sorted(products, key=lambda x: x[sort_key], reverse=not ascending)
    
    def format_product_info(self, product, index):
        """상품 정보 포맷팅"""
        ad_mark = "🔴광고" if product.get('is_ad') else ""
        
        if product['quantity'] > 1:
            price_info = f"💰 총 {product['price']:,}원 (개당 약 {int(product['unit_price']):,}원 x {product['quantity']}개)"
        else:
            price_info = f"💰 {product['price']:,}원"
        
        rating_info = ""
        if product.get('rating') is not None:
            stars = "⭐" * int(product['rating'])
            rating_info = f"\n⭐ 별점: {product['rating']:.1f} {stars}"
        
        if product.get('review_count') is not None:
            rating_info += f"\n💬 리뷰: {product['review_count']:,}개"
        
        seller_info = ""
        if product.get('seller_satisfaction'):
            seller_info += f"\n👍 판매자 만족: {product['seller_satisfaction']}"
        if product.get('seller_response'):
            seller_info += f"\n⚡ 응답률: {product['seller_response']}"
        if product.get('seller_sales'):
            seller_info += f"\n📊 판매량: {product['seller_sales']}"
        
        return f"""
{index}. {product['name'][:70]}...
{price_info}
🚚 배송: {product['delivery']} {ad_mark}{rating_info}{seller_info}
🔗 {product['link']}
"""
    
    def close(self):
        """브라우저 종료"""
        self.driver.quit()