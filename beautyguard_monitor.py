#!/usr/bin/env python3
import os
import sys
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime

CRITICAL_KEYWORDS = [
'환불', '소송', '고소', '신고', '망침', '망했', '망함', '최악', '다시는 안',
'돈 아깝', '싸가지', '기분 더럽', '피났', '피남', '화상', '스킨탈락', '모낭염', '염증'
]

SUSPICIOUS_KEYWORDS = [
'녹았', '녹음', '탔어', '탄머리', '얼룩', '얼룩덜룩', '짝짝이',
'파츠', '큐티클', '들뜸', '깨짐', '벗겨짐', '유지력',
'인그로운', '붉은기', '따가움', '가려움',
'불친절', '대기', '실망', '비추', '손상'
]

POSITIVE_WORDS = [
'만족', '추천', 'ㅊㅊ', '예쁘', '이쁘', '살려', '감사', '대만족', '좋았', '좋아',
'찰떡', '최고', '친절', '감동', '정착', '맞춰주', '해결', '꼼꼼', '유지력 짱', '안 아프'
]

HEADERS = {
'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
'Referer': 'https://m.place.naver.com/',
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8'
}

HISTORY_FILE = 'seen_reviews.json'

def load_seen_reviews():
\if os.path.exists(HISTORY_FILE):
\try:
\with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
\return set(json.load(f))
\except Exception:
\return set()
\return set()

def save_seen_reviews(seen_set):
\items = list(seen_set)[-500:]
\with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
\json.dump(items, f, ensure_ascii=False, indent=2)

def fetch_reviews(place_id):
\url = f"https://m.place.naver.com/place/{place_id}/review/visitor"
\req = urllib.request.Request(url, headers=HEADERS)
\try:
\with urllib.request.urlopen(req, timeout=10) as resp:
\content = resp.read().decode('utf-8')
\except Exception:
\return [], "매장"

\m = re.search(r'window.APOLLO_STATE\s*=\s*({.*?});', content, re.DOTALL)
\if not m:
\return [], "매장"

\apollo = json.loads(m.group(1))
\business_name = "매장"
\for k, v in apollo.items():
\if k.startswith('PlaceDetailBase:') and 'name' in v:
\business_name = v['name']
\break

\reviews = []
\for k, v in apollo.items():
\if k.startswith('VisitorReview:'):
\review_id = v.get('id') or v.get('reviewId')
\body = v.get('body') or ""
\rating = v.get('rating')
\created = v.get('created') or ""
\designer = (v.get('item') or {}).get('name') or "담당 디자이너"

\reviews.append({
'id': str(review_id),
'business_name': business_name,
'rating': rating,
'body': body,
'created': created,
'designer': designer
})
\return reviews, business_name

def is_real_danger_review(body, rating):
\if rating is not None and rating >= 4:
\if any(w in body for w in ['사기', '고소', '신고']):
\return True, "🚨 [심각] 법적 분쟁 리스크"
\return False, None

\if rating is not None and rating <= 3:
\if rating <= 2 or any(w in body for w in CRITICAL_KEYWORDS):
\return True, "🚨 [심각] 시술 클레임 및 분쟁 리스크"
\return True, "⚠️ [주의] 고객 불만 제기"

\has_critical = any(w in body for w in CRITICAL_KEYWORDS)
\has_suspicious = any(w in body for w in SUSPICIOUS_KEYWORDS)
\positive_count = sum(1 for w in POSITIVE_WORDS if w in body)

\if positive_count >= 2 and not has_critical:
\return False, None

\if has_critical:
\return True, "🚨 [심각] 시술 클레임 리스크"
\elif has_suspicious and positive_count == 0:
\return True, "⚠️ [주의] 고객 불만 제기"

\return False, None

def generate_positive_replies(business_name, body, designer):
\item_point = "시술"
\if '네일' in body or '파츠' in body or '패디' in body:
\item_point = "네일 아트 디자인"
\elif '속눈썹' in body or '펌' in body:
\item_point = "속눈썹 컬링"
\elif '왁싱' in body or '피부' in body:
\item_point = "피부 진정 케어"
\elif '염색' in body or '커트' in body or '펌' in body:
\item_point = "헤어 스타일링"

\reply_1 = (
\f"안녕하세요 고객님! {business_name} {designer}입니다 🤎 "
\f"정성 가득한 사진과 리뷰 남겨주셔서 진심으로 감사드려요. "
\f"오늘 받으신 {item_point}이 마음에 쏙 드셨다니 저도 정말 행복합니다! "
\f"예쁘게 유지하시고, 다음 케어 주기 때 또 기분 좋게 뵙겠습니다. 늘 좋은 하루 보내세요! ✨"
)

\reply_2 = (
\f"안녕하세요 고객님, {business_name}입니다 :) "
\f"믿고 방문해 주셨는데 만족스러운 결과를 드려 큰 보람을 느낍니다! "
\f"앞으로도 꼼꼼하고 세심한 시술로 만족을 드릴게요. 소중한 추천 리뷰 감사합니다 🫶"
)
\return reply_1, reply_2

def generate_danger_replies(business_name, body):
\reply_a = (
\f"안녕하세요 고객님, {business_name} 대표원장입니다. "
\f"소중한 시간 내어 방문해 주셨는데 만족을 드리지 못해 송구한 마음입니다. "
\f"시술 상태 확인과 정확한 해결책 마련을 위해 제가 직접 상담 도와드리고자 합니다. "
\f"편하신 시간에 매장으로 연락 주시면 성심껏 점검해 드리겠습니다."
)
\reply_b = (
\f"안녕하세요 고객님, {business_name}입니다. "
\f"시술 후 불편함을 겪고 계신 점 확인했습니다. "
\f"현재 상태에 맞춘 보완 케어 및 안내를 도와드리고자 하니, 매장으로 연락 부탁드립니다."
)
\rule = "온라인상 과실 인정 및 환불 확답 절대 금지. 대면 진단 유도."
\return rule, reply_a, reply_b

def send_alert(token, chat_id, r, is_danger, risk_title=None, rule=None, replies=None):
\if is_danger:
\r_a, r_b = replies
\msg = f"🚨 [뷰티가드 긴급 불만 사이렌]\n\n📍 매장: {r['business_name']}\n✂️ 담당: {r['designer']}\n⭐️ 별점: {r.get('rating', '미표기')}점 ({r['created']})\n💬 고객 리뷰:\n"{r['body']}"\n───────────────\n{risk_title}\n• 대응 원칙: {rule}\n\n📋 원클릭 복사용 안전 답글 2종\n\n[타입 A. 대표원장 책임 상담형 (추천)]\n"{r_a}"\n\n[타입 B. 사후 보완 케어 안내형]\n"{r_b}"\n───────────────\n✨ 뷰티가드가 24시간 원장님의 매장 평판을 지킵니다."
\else:
\r_1, r_2 = replies
\msg = f"🌟 [뷰티가드 신규 칭찬 리뷰 알림]\n\n📍 매장: {r['business_name']}\n✂️ 담당: {r['designer']}\n⭐️ 별점: {r.get('rating', 5)}점 ({r['created']})\n💬 고객 리뷰:\n"{r['body']}"\n───────────────\n💌 복사해서 바로 쓰는 맞춤 감동 답글 2종\n\n[옵션 1. 친근 & 감동 감사형 (추천)]\n"{r_1}"\n\n[옵션 2. 깔끔한 재방문 유도형]\n"{r_2}"\n───────────────\n💡 네이버 플레이스 리뷰 답글률이 100%에 가까울수록 네이버 지도 검색 순위(노출 지수)가 올라갑니다!"

\data = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg}).encode()
\req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
\try:
\urllib.request.urlopen(req, timeout=10)
\except Exception as e:
\print(f"[-] 텔레그램 발송 오류: {e}")

def main():
\bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '9291440250:AAHL88CFDBIGOs9ZyNUdhFTMkmpimVdIcDY')

\salons_path = 'salons.json'
\if not os.path.exists(salons_path):
\salons = [{
"name": "준오헤어 명동4호점 (테스트 매장)",
"place_id": "37207274",
"chat_id": "8891231833"
}]
\with open(salons_path, 'w', encoding='utf-8') as f:
\json.dump(salons, f, ensure_ascii=False, indent=2)
\else:
\with open(salons_path, 'r', encoding='utf-8') as f:
\salons = json.load(f)

\seen = load_seen_reviews()
\new_seen = set(seen)
\alerts_sent = 0

\print(f"[*] 총 {len(salons)}개 뷰티샵 감시 시작 ({datetime.now()})")

\for s in salons:
\p_id = str(s['place_id'])
\c_id = str(s['chat_id'])
\reviews, b_name = fetch_reviews(p_id)
\print(f"  - [{b_name}] 리뷰 {len(reviews)}개 확인")

\for r in reviews:
\r_id = r['id']
\if r_id in seen:
\continue
\new_seen.add(r_id)

\body = r['body']
\rating = r['rating']

\is_danger, risk = is_real_danger_review(body, rating)

\if is_danger:
\print(f"    🚨 불만 리뷰 감지: ID {r_id}")
\rule, a, b = generate_danger_replies(b_name, body)
\send_alert(bot_token, c_id, r, is_danger=True, risk_title=risk, rule=rule, replies=(a, b))
\alerts_sent += 1
\else:
\print(f"    🌟 칭찬 리뷰 감지: ID {r_id}")
\r1, r2 = generate_positive_replies(b_name, body, r['designer'])
\send_alert(bot_token, c_id, r, is_danger=False, replies=(r1, r2))
\alerts_sent += 1

\save_seen_reviews(new_seen)
\print(f"[+] 감시 완료: 총 {alerts_sent}건의 알림 발송됨")

if name == 'main':
\main()
