import streamlit as st
from st11_scraper import ST11Scraper
from telegram_bot import TelegramBot
import time
import webbrowser

# 페이지 설정
st.set_page_config(
    page_title="🛒 11번가 쇼핑 검색",
    page_icon="🛒",
    layout="wide"
)

# 타이틀
st.title("🛒 11번가 쇼핑 검색")
st.markdown("---")

# 사이드바
st.sidebar.header("⚙️ 검색 설정")

# 검색 키워드
keywords_input = st.sidebar.text_input(
    "검색 키워드 (쉼표로 구분)",
    placeholder="예: 친환경 세제, 비건 샴푸"
)

# 최대 상품 개수
max_option = st.sidebar.radio(
    "최대 상품 개수",
    options=["제한 있음", "최대로 (전체)"]
)

if max_option == "제한 있음":
    max_items = st.sidebar.slider("수집할 상품 개수", 10, 200, 50, 10)
else:
    max_items = 999999
    st.sidebar.info("ℹ️ 페이지의 모든 상품 수집")

# 정렬 방식
sort_option = st.sidebar.radio(
    "정렬 방식",
    options=["총 가격 낮은 순", "총 가격 높은 순", "개당 가격 낮은 순", "개당 가격 높은 순"]
)

# 상세 정보 수집
fetch_details = st.sidebar.checkbox(
    "⭐ 상위 20개 상세 정보 수집",
    value=False,
    help="별점, 리뷰, 판매자 정보 (시간이 더 걸립니다)"
)

# 텔레그램 전송
send_telegram = st.sidebar.checkbox("텔레그램으로 결과 전송")

# 브라우저 표시
show_browser = st.sidebar.checkbox("브라우저 보이기", value=False)

st.sidebar.markdown("---")

# 세션 스테이트 초기화
if 'search_results' not in st.session_state:
    st.session_state.search_results = None

# 검색 버튼
if st.sidebar.button("🔍 검색 시작", type="primary", use_container_width=True):
    if not keywords_input:
        st.error("❌ 검색 키워드를 입력해주세요!")
    else:
        search_keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🚀 크롤러 초기화 중...")
            scraper = ST11Scraper(headless=not show_browser)
            progress_bar.progress(10)
            
            all_results = []
            
            # 각 키워드 검색
            for idx, keyword in enumerate(search_keywords):
                status_text.text(f"🔍 '{keyword}' 검색 중... ({idx+1}/{len(search_keywords)})")
                products = scraper.search_products(keyword, max_items=max_items)
                
                if products:
                    all_results.extend(products)
                
                progress_bar.progress(10 + int(50 * (idx + 1) / len(search_keywords)))
                time.sleep(1)
            
            # 중복 제거
            status_text.text("🔄 중복 제거 중...")
            seen_links = set()
            unique_results = []
            for product in all_results:
                if product['link'] not in seen_links:
                    seen_links.add(product['link'])
                    unique_results.append(product)
            
            progress_bar.progress(65)
            
            # 정렬
            status_text.text("📊 정렬 중...")
            sort_by_unit = "개당 가격" in sort_option
            ascending = "낮은 순" in sort_option
            unique_results = scraper.sort_by_price(unique_results, ascending=ascending, by_unit=sort_by_unit)
            
            progress_bar.progress(75)
            
            # 상세 정보 수집
            if fetch_details:
                status_text.text("⭐ 상위 20개 상품의 상세 정보 수집 중...")
                normal_products = [p for p in unique_results if not p.get('is_ad')]
                if normal_products:
                    scraper.fetch_product_details(normal_products, max_count=20)
                progress_bar.progress(85)
            
            # 텔레그램 전송
            if send_telegram and unique_results:
                status_text.text("📤 텔레그램 전송 중...")
                try:
                    telegram = TelegramBot()
                    
                    normal_products = [p for p in unique_results if not p.get('is_ad')]
                    ad_products = [p for p in unique_results if p.get('is_ad')]
                    
                    # 일반 상품 전송
                    if normal_products:
                        message = f"🛒 <b>11번가 검색 결과 (일반 상품)</b>\n"
                        message += f"검색어: {', '.join(search_keywords)}\n"
                        message += f"정렬: {sort_option}\n"
                        message += f"총 {len(normal_products)}개\n"
                        message += "=" * 40 + "\n\n"
                        
                        for idx, product in enumerate(normal_products[:15], 1):
                            message += scraper.format_product_info(product, idx)
                            message += "-" * 40 + "\n"
                        
                        if len(message) > 4000:
                            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                            for part in parts:
                                telegram.send_message(part)
                                time.sleep(1)
                        else:
                            telegram.send_message(message)
                    
                    # 광고 상품 전송
                    if ad_products:
                        time.sleep(2)
                        message = f"🔴 <b>11번가 검색 결과 (광고 상품)</b>\n"
                        message += f"검색어: {', '.join(search_keywords)}\n"
                        message += f"총 {len(ad_products)}개\n"
                        message += "=" * 40 + "\n\n"
                        
                        for idx, product in enumerate(ad_products[:15], 1):
                            message += scraper.format_product_info(product, idx)
                            message += "-" * 40 + "\n"
                        
                        if len(message) > 4000:
                            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                            for part in parts:
                                telegram.send_message(part)
                                time.sleep(1)
                        else:
                            telegram.send_message(message)
                    
                    st.sidebar.success("✅ 텔레그램 전송 완료!")
                except Exception as e:
                    st.sidebar.error(f"❌ 텔레그램 전송 실패: {e}")
            
            progress_bar.progress(100)
            status_text.text("✅ 검색 완료!")
            
            scraper.close()
            st.session_state.search_results = {
                'products': unique_results,
                'keywords': search_keywords,
                'sort_option': sort_option
            }
            
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 에러 발생: {e}")
            import traceback
            st.code(traceback.format_exc())

# 결과 표시
if st.session_state.search_results:
    data = st.session_state.search_results
    unique_results = data['products']
    search_keywords = data['keywords']
    sort_option = data['sort_option']
    
    normal_products = [p for p in unique_results if not p.get('is_ad')]
    ad_products = [p for p in unique_results if p.get('is_ad')]
    
    st.success(f"🎉 총 {len(unique_results)}개 제품 (일반 {len(normal_products)}개 + 광고 {len(ad_products)}개)")
    
    # 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("일반 상품", f"{len(normal_products)}개")
    with col2:
        st.metric("광고 상품", f"{len(ad_products)}개")
    with col3:
        avg_price = sum(p['price'] for p in normal_products) / len(normal_products) if normal_products else 0
        st.metric("평균 가격", f"{int(avg_price):,}원")
    with col4:
        free_delivery = sum(1 for p in unique_results if '무료' in p['delivery'])
        st.metric("무료배송", f"{free_delivery}개")
    
    st.markdown("---")
    
    # 탭
    tab1, tab2 = st.tabs(["📦 일반 상품", "🔴 광고 상품"])
    
    with tab1:
        if normal_products:
            st.info(f"ℹ️ {sort_option}")
            
            for idx, product in enumerate(normal_products, 1):
                with st.expander(f"**{idx}. {product['name'][:80]}...**"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # 가격 정보
                        if product['quantity'] > 1:
                            st.write(f"💰 **총 가격:** {product['price']:,}원")
                            st.write(f"📦 **개당 가격:** 약 {int(product['unit_price']):,}원 (x{product['quantity']}개)")
                        else:
                            st.write(f"💰 **가격:** {product['price']:,}원")
                        
                        st.write(f"🚚 **배송:** {product['delivery']}")
                        
                        # 별점/리뷰
                        if product.get('rating') is not None:
                            stars = "⭐" * int(product['rating'])
                            st.write(f"⭐ **별점:** {product['rating']:.1f} {stars}")
                        
                        if product.get('review_count') is not None:
                            st.write(f"💬 **리뷰:** {product['review_count']:,}개")
                        
                        # 판매자 정보
                        if product.get('seller_satisfaction'):
                            st.write(f"👍 **판매자 만족:** {product['seller_satisfaction']}")
                        if product.get('seller_response'):
                            st.write(f"⚡ **응답률:** {product['seller_response']}")
                        if product.get('seller_sales'):
                            st.write(f"📊 **판매량:** {product['seller_sales']}")
                    
                    with col2:
                        st.link_button("🔗 상품 보기", product['link'], use_container_width=True)
                        
                        # 리뷰 보기 버튼
                        if product.get('review_count') and product['review_count'] > 0:
                            review_url = f"{product['link']}#review"
                            st.link_button("💬 리뷰 보기", review_url, use_container_width=True)
        else:
            st.warning("일반 상품이 없습니다.")
    
    with tab2:
        if ad_products:
            st.warning(f"⚠️ 광고 상품 {len(ad_products)}개")
            
            for idx, product in enumerate(ad_products, 1):
                with st.expander(f"**{idx}. 🔴 {product['name'][:80]}...**"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        if product['quantity'] > 1:
                            st.write(f"💰 **총 가격:** {product['price']:,}원")
                            st.write(f"📦 **개당 가격:** 약 {int(product['unit_price']):,}원")
                        else:
                            st.write(f"💰 **가격:** {product['price']:,}원")
                        
                        st.write(f"🚚 **배송:** {product['delivery']}")
                        st.write("🔴 **광고 상품**")
                    
                    with col2:
                        st.link_button("🔗 상품 보기", product['link'], use_container_width=True)
        else:
            st.info("광고 상품이 없습니다.")
    
    # 다운로드
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if normal_products:
            txt = f"11번가 검색 결과 (일반 상품)\n{'='*70}\n\n"
            txt += f"검색어: {', '.join(search_keywords)}\n"
            txt += f"정렬: {sort_option}\n\n"
            
            for idx, p in enumerate(normal_products, 1):
                txt += f"{idx}. {p['name']}\n"
                txt += f"   가격: {p['price']:,}원\n"
                if p['quantity'] > 1:
                    txt += f"   개당: {int(p['unit_price']):,}원 ({p['quantity']}개)\n"
                txt += f"   배송: {p['delivery']}\n"
                if p.get('rating'):
                    txt += f"   별점: {p['rating']:.1f}\n"
                if p.get('review_count'):
                    txt += f"   리뷰: {p['review_count']:,}개\n"
                if p.get('seller_satisfaction'):
                    txt += f"   판매자 만족: {p['seller_satisfaction']}\n"
                if p.get('seller_response'):
                    txt += f"   응답률: {p['seller_response']}\n"
                if p.get('seller_sales'):
                    txt += f"   판매량: {p['seller_sales']}\n"
                txt += f"   링크: {p['link']}\n\n"
            
            st.download_button(
                "📥 일반 상품 다운로드",
                txt,
                f"11st_normal_{int(time.time())}.txt",
                use_container_width=True
            )
    
    with col2:
        if ad_products:
            txt = f"11번가 검색 결과 (광고 상품)\n{'='*70}\n\n"
            txt += f"검색어: {', '.join(search_keywords)}\n\n"
            
            for idx, p in enumerate(ad_products, 1):
                txt += f"{idx}. {p['name']}\n"
                txt += f"   가격: {p['price']:,}원\n"
                txt += f"   배송: {p['delivery']}\n"
                txt += f"   링크: {p['link']}\n"
                txt += f"   [광고]\n\n"
            
            st.download_button(
                "📥 광고 상품 다운로드",
                txt,
                f"11st_ads_{int(time.time())}.txt",
                use_container_width=True
            )