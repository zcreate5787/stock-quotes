"""장중 시세 수집. 네이버 금융 모바일 목록에서 코스피·코스닥 전 종목 현재가를 받아 data/quotes.json 에 쓴다.
보유 종목을 드러내지 않도록 전 종목을 받는다. extra.txt 의 코드(ETF 등)는 개별로 받는다."""
import json, os, sys, time, datetime, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36', 'Referer': 'https://m.stock.naver.com/'}

def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            err = e; time.sleep(1 + i)
    raise err

def num(x):
    try: return int(float(str(x).replace(',', '')))
    except Exception: return None

rows, errors, sample = {}, [], None
for market in ('KOSPI', 'KOSDAQ'):
    page = 1
    while page <= 40:
        try:
            j = get('https://m.stock.naver.com/api/stocks/marketValue/%s?page=%d&pageSize=100' % (market, page))
        except Exception as e:
            errors.append('%s p%d: %s' % (market, page, e)); break
        items = j.get('stocks') or []
        if not items: break
        if sample is None: sample = items[0]
        for it in items:
            c = num(it.get('closePrice'))
            if not c: continue
            r = {'c': c}
            for k, f in (('o', 'openPrice'), ('h', 'highPrice'), ('l', 'lowPrice')):
                v = num(it.get(f))
                if v: r[k] = v
            rows[it.get('itemCode')] = r
        if len(items) < 100: break
        page += 1; time.sleep(0.15)

extra = [x.strip() for x in open('extra.txt').read().split() if x.strip() and not x.startswith('#')] if os.path.exists('extra.txt') else []
for code in extra:
    try:
        j = get('https://m.stock.naver.com/api/stock/%s/basic' % code)
        c = num(j.get('closePrice'))
        if c: rows[code] = {'c': c}
        else: errors.append('%s: 가격 없음' % code)
    except Exception as e:
        errors.append('%s: %s' % (code, e))

kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
out = {'at': kst.strftime('%Y-%m-%d %H:%M'), 'd': kst.strftime('%Y-%m-%d'), 'src': '네이버 금융', 'n': len(rows), 'errors': errors[:20], 'rows': rows}
print('종목', len(rows), '| 오류', len(errors), errors[:5]); print('표본', json.dumps(sample, ensure_ascii=False)[:600])
if len(rows) < 1000: sys.exit('받은 종목이 너무 적어 파일을 바꾸지 않습니다.')
json.dump(out, open('data/quotes.json', 'w'), ensure_ascii=False, separators=(',', ':'))
