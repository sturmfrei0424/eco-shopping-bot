from st11_scraper import ST11Scraper
from telegram_bot import TelegramBot
import time

def main():
    print("=" * 70)
    print("🛒 11번가 쇼핑 검색")
    print("=" * 70)
    
    # 검색 키워드
    print("\n📝 검색할 키워드를 입력하세요 (쉼표로 구분)")
    print("예시: 친환경 세제, 비건 샴푸, 무포장 리필")
    keyword_input = input("➤ 키워드: ").strip()
    
    if not keyword_input:
        print("❌ 키워드를 입력해주세요!")
        return
    
    search_keywords = [k.strip() for k in keyword_input.split(',') if k.strip()]
    
    # 최대 상품 개수
    print("\n📝 수집할 최대 상품 개수 (기본: 100, 0 입력시 전체)")
    max_input = input("➤ 개수: ").strip()
    if max_input == '0':
        max_items = 999999
    else:
        max_items = int(max_input) if max_input.isdigit() else 100
    
    # 정렬 방식
    print("\n📝 정렬 방식을 선택하세요:")
    print("1. 총 가격 낮은 순 (기본)")
    print("2. 개당 가격 낮은 순 (묶음 상품 고려)")
    sort_choice = input("➤ 선택 (1 또는 2): ").strip()
    sort_by_unit = (sort_choice == '2')
    
    # 텔레그램 전송
    print("\n📝 텔레그램으로 결과를 전송하시겠습니까? (y/n)")
    send_telegram = input("➤ 전송: ").strip().lower() == 'y'
    
    # 브라우저 표시
    print("\n📝 브라우저를 보이게 하시겠습니까? (y/n)")
    show_browser = input("➤ 보이기: ").strip().lower() == 'y'
    
    print("\n" + "=" * 70)
    print("🚀 검색 시작!")
    print("=" * 70 + "\n")
    
    # 초기화
    scraper = ST11Scraper(headless=not show_browser)
    if send_telegram:
        telegram = TelegramBot()
    
    all_results = []
    
    try:
        for keyword in search_keywords:
            products = scraper.search_products(keyword, max_items=max_items)
            
            if products:
                print(f"   📦 '{keyword}': {len(products)}개 수집됨\n")
                all_results.extend(products)
            
            time.sleep(2)
        
        # 중복 제거
        seen_links = set()
        unique_results = []
        for product in all_results:
            if product['link'] not in seen_links:
                seen_links.add(product['link'])
                unique_results.append(product)
        
        # 정렬
        unique_results = scraper.sort_by_price(unique_results, ascending=True, by_unit=sort_by_unit)
        
        # 결과 출력
        if unique_results:
            print("\n" + "=" * 70)
            sort_text = "개당 가격" if sort_by_unit else "총 가격"
            print(f"🎉 총 {len(unique_results)}개 제품 발견! ({sort_text} 낮은 순)")
            print("=" * 70 + "\n")
            
            # 상위 20개 출력
            display_count = min(20, len(unique_results))
            for idx, product in enumerate(unique_results[:display_count], 1):
                print(scraper.format_product_info(product, idx))
                print("-" * 70)
            
            if len(unique_results) > 20:
                print(f"\n(... 외 {len(unique_results) - 20}개 상품 더 있음)")
            
            # 텔레그램 전송
            if send_telegram:
                print("\n📤 텔레그램 전송 중...")
                message = f"🛒 <b>11번가 검색 결과</b>\n"
                message += f"검색어: {', '.join(search_keywords)}\n"
                message += f"정렬: {sort_text} 낮은 순\n"
                message += f"총 {len(unique_results)}개 발견!\n"
                message += "=" * 40 + "\n\n"
                
                for idx, product in enumerate(unique_results[:15], 1):
                    message += scraper.format_product_info(product, idx)
                    message += "-" * 40 + "\n"
                
                if len(message) > 4000:
                    parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                    for part in parts:
                        telegram.send_message(part)
                        time.sleep(1)
                else:
                    telegram.send_message(message)
                
                print("✅ 텔레그램 전송 완료!")
            
            # 파일 저장
            print("\n📝 결과를 파일로 저장하시겠습니까? (y/n)")
            save_file = input("➤ 저장: ").strip().lower() == 'y'
            
            if save_file:
                filename = f"11st_results_{int(time.time())}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=" * 70 + "\n")
                    f.write("11번가 검색 결과\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(f"검색어: {', '.join(search_keywords)}\n")
                    f.write(f"정렬: {sort_text} 낮은 순\n")
                    f.write(f"총 {len(unique_results)}개 발견\n")
                    f.write("=" * 70 + "\n\n")
                    
                    for idx, product in enumerate(unique_results, 1):
                        f.write(f"{idx}. {product['name']}\n")
                        if product['quantity'] > 1:
                            f.write(f"   총 가격: {product['price']:,}원\n")
                            f.write(f"   개당 가격: 약 {int(product['unit_price']):,}원 ({product['quantity']}개)\n")
                        else:
                            f.write(f"   가격: {product['price']:,}원\n")
                        f.write(f"   배송: {product['delivery']}\n")
                        f.write(f"   링크: {product['link']}\n")
                        if product.get('is_ad'):
                            f.write(f"   [광고]\n")
                        f.write("\n")
                
                print(f"✅ {filename}에 저장 완료!")
        else:
            print("\n" + "=" * 70)
            print("❌ 검색 결과가 없습니다.")
            print("=" * 70)
            if send_telegram:
                telegram.send_message(f"🔍 '{', '.join(search_keywords)}' 검색 결과가 없습니다 😢")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        print("\n" + "=" * 70)
        print("🎉 프로그램 종료!")
        print("=" * 70)

if __name__ == "__main__":
    main()