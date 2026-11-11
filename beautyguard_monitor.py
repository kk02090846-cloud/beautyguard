#!/usr/bin/env python3
import os, sys, json, re, urllib.request, urllib.parse
from datetime import datetime

CRITICAL_KEYWORDS = ['환불', '소송', '고소', '신고', '망침', '망했', '망함', '최악', '다시는 안', '돈 아깝', '싸가지', '기분 더럽', '피났', '피남', '화상', '스킨탈락', '모낭염', '염증']
SUSPICIOUS_KEYWORDS = ['녹았', '녹음', '탔어', '탄머리', '얼룩', '얼룩덜룩', '짝짝이', '파츠', '큐티클', '들뜸', '깨짐', '벗겨짐', '유지력', '인그로운', '붉은기', '따가움', '가려움', '불친절', '대기', '실망', '비추', '손상']
POSITIVE_WORDS = ['만족', '추천', 'ㅊㅊ', '예쁘', '이쁘', '살려', '감사', '대만족', '좋았', '좋아', '찰떡', '최고', '친절', '감동', '정착', '맞춰주', '해결', '꼼꼼', '유지력 짱', '안 아프']
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', 'Referer': 'https://m.place.naver.com/', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8'}
HISTORY_FILE = 'seen_reviews.json'

def load_seen_reviews():
if os.path.exists(HISTORY_FILE):
\try:
\with open(HISTORY_FILE, 'r', encoding='utf-8') as f: return set(json.load(f))
\except: return set()
\return set()

def save_seen_reviews(seen_set):
\with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump(list(seen_set)[-500:], f, ensure_ascii=False, indent=2)

def fetch_reviews(place_id):
\url = f"https://m.place.naver.com/place/{place_id}/review/visitor"
\req = urllib.request.Request(url, headers=HEADERS)
\try:
\with urllib.request.urlopen(req, timeout=10) as resp: content = resp.read().decode('utf-8')
\except: return [], "매장"
\m = re.search(r'window.APOLLO_STATE\s*=\s*({.*?});', content, re.DOTALL)
\if not m: return [], "매장"
\apollo = json.loads(m.group(1))
\name = "매장"
\for k, v in apollo.items():
\if k.startswith('PlaceDetailBase:') and 'name' in v: name = v['name']; break
\reviews = []
\for k, v in apollo.items():
\if k.startswith('VisitorReview:'):
\reviews.append({
'id': str(v.get('id') or v.get('reviewId')),
'business_name': name,
'rating': v.get('rating'),
'body': v.get('body') or "",
'created': v.get('created') or "",
'designer': (v.get('item') or {}).get('name') or "담당 디자이너"
})
\return reviews, name

def is_real_danger_review(body, rating):
\if rating is not None and rating >= 4:
\return (True, "🚨 [심각] 법적 분쟁 리스크") if any(w in body for w in ['사기', '고소', '신고']) else (False, None)
\if rating is not None and rating <= 3:
\return (True, "🚨 [심각] 시술 클레임 리스크") if (rating <= 2 or any(w in body for w in CRITICAL_KEYWORDS)) else (True, "⚠️ [주의] 고객 불만 제기")
\has_crit = any(w in body for w in CRITICAL_KEYWORDS)
\pos_cnt = sum(1 for w in POSITIVE_WORDS if w in body)
\if pos_cnt >= 2 and not has_crit: return False, None
\if has_crit: return True, "🚨 [심각] 시술 클레임 리스크"
\if any(w in body for w in SUSPICIOUS_KEYWORDS) and pos_cnt == 0: return True, "⚠️ [주의] 고객 불만 제기"
\return False, None

def generate_positive_replies(name, body, designer):
\item = "헤어 스타일링" if any(w in body for w in ['염색','커트','펌']) else ("네일 아트" if any(w in body for w in ['네일','파츠','패디']) else "맞춤 케어")
\r1 = f"안녕하세요 고객님! {name} {designer}입니다 🤎 소중한 리뷰 감사드려요. 오늘 시술받으신 {item}이 마음에 드셨다니 정말 행복합니다! 예쁘게 관리하시고 다음 케어 주기 때 또 기분 좋게 뵙겠습니다 ✨"
\r2 = f"안녕하세요 고객님, {name}입니다 :) 만족스러운 결과를 드려 큰 보람을 느낍니다! 앞으로도 꼼꼼하고 세심하게 모시겠습니다. 소중한 추천 감사드려요 🫶"
\return r1, r2

def generate_danger_replies(name, body):
\r_a = f"안녕하세요 고객님, {name} 대표원장입니다. 소중한 시간 내어 찾아주셨는데 만족을 드리지 못해 송구한 마음입니다. 시술 상태 확인과 정확한 해결책 안내를 위해 제가 직접 상담 도와드리고자 하니, 편하신 시간에 매장으로 연락 부탁드립니다."
\r_b = f"안녕하세요 고객님, {name}입니다. 시술 후 불편함을 겪고 계신 점 확인했습니다. 현재 상태에 맞춘 보완 케어 및 점검을 도와드리고자 하니 매장으로 연락 부탁드립니다."
\return "온라인 과실 인정 금지, 대면 진단 유도", r_a, r_b

def send_alert(token, chat_id, r, is_danger, risk_title=None, rule=None, replies=None):
\if is_danger:
\ra, rb = replies
\msg = f"🚨 [뷰티가드 긴급 불만 사이렌]\n\n📍 매장: {r['business_name']}\n✂️ 담당: {r['designer']}\n⭐️ 별점: {r.get('rating', '미표기')}점 ({r['created']})\n💬 고객 리뷰:\n"{r['body']}"\n───────────────\n{risk_title}\n• 대응 원칙: {rule}\n\n📋 안전 답글 2종\n[타입 A. 대표원장 책임 상담형]\n"{ra}"\n\n[타입 B. 사후 보완 케어형]\n"{rb}"\n───────────────\n✨ 뷰티가드가 24시간 원장님의 매장 평판을 지킵니다."
\else:
\r1, r2 = replies
\msg = f"🌟 [뷰티가드 신규 칭찬 리뷰 알림]\n\n📍 매장: {r['business_name']}\n✂️ 담당: {r['designer']}\n⭐️ 별점: {r.get('rating', 5)}점 ({r['created']})\n💬 고객 리뷰:\n"{r['body']}"\n───────────────\n💌 맞춤 감동 답글 2종\n[옵션 1. 친근 & 감동형]\n"{r1}"\n\n[옵션 2. 깔끔 재방문형]\n"{r2}"\n───────────────\n💡 리뷰 답글률이 100%에 가까울수록 네이버 플레이스 검색 순위가 올라갑니다!"
\data = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg}).encode()
\urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=10)

def main():
\token = os.environ.get('TELEGRAM_BOT_TOKEN', '9291440250:AAHL88CFDBIGOs9ZyNUdhFTMkmpimVdIcDY')
\salons = json.load(open('salons.json', encoding='utf-8')) if os.path.exists('salons.json') else [{'name':'준오헤어 명동4호점','place_id':'37207274','chat_id':'8891231833'}]
\seen = load_seen_reviews()
\new_seen = set(seen)
\for s in salons:
\reviews, name = fetch_reviews(str(s['place_id']))
\for r in reviews:
\if r['id'] in seen: continue
\new_seen.add(r['id'])
\danger, risk = is_real_danger_review(r['body'], r['rating'])
\if danger:
\rule, a, b = generate_danger_replies(name, r['body'])
\send_alert(token, str(s['chat_id']), r, True, risk, rule, (a, b))
\else:
\r1, r2 = generate_positive_replies(name, r['body'], r['designer'])
\send_alert(token, str(s['chat_id']), r, False, replies=(r1, r2))
\save_seen_reviews(new_seen)

if name == 'main': main()
