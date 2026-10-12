"""장중 시세 수집. 코스피·코스닥 전 종목 현재가를 받아 data/quotes.json 에 쓴다.
보유 종목을 드러내지 않도록 전 종목을 받는다. 여러 출처를 차례로 시도하고 과정은 data/log.txt 에 남긴다."""
import json, os, time, datetime, urllib.request, urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
LOG = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.append(s)

def http(url, data=None, headers=None, tries=2):
    h = {'User-Agent': UA}; h.update(headers or {})
    body = urllib.parse.urlencode(data).encode() if data else None
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=15) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            err = e; time.sleep(1)
    raise err

def num(x):
    try: return int(float(str(x).replace(',', '')))
    except Exception: return None

kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)

def krx():
    rows = {}
    ymd = kst.strftime('%Y%m%d')
    for bld, mkt in (('dbms/MDC/STAT/standard/MDCSTAT01501', {'mktId': 'ALL'}), ('dbms/MDC/STAT/standard/MDCSTAT04301', {})):
        d = {'bld': bld, 'locale': 'ko_KR', 'trdDd': ymd, 'share': '1', 'money': '1', 'csvxls_isNo': 'false'}; d.update(mkt)
        try:
            t = http('http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', d, {'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd', 'X-Requested-With': 'XMLHttpRequest'})
            j = json.loads(t); items = j.get('OutBlock_1') or j.get('output') or []
            log('KRX', bld[-12:], len(items), t[:150].replace('\n', ' '))
            for it in items:
                c = num(it.get('TDD_CLSPRC'))
                if not c: continue
                r = {'c': c}
                for k, f in (('o', 'TDD_OPNPRC'), ('h', 'TDD_HGPRC'), ('l', 'TDD_LWPRC')):
                    v = num(it.get(f))
                    if v: r[k] = v
                rows[it.get('ISU_SRT_CD')] = r
        except Exception as e:
            log('KRX 실패', bld[-12:], repr(e)[:200])
    return rows

def naver():
    rows = {}
    for market in ('KOSPI', 'KOSDAQ'):
        for page in range(1, 41):
            try:
                t = http('https://m.stock.naver.com/api/stocks/marketValue/%s?page=%d&pageSize=100' % (market, page), headers={'Referer': 'https://m.stock.naver.com/'})
                items = json.loads(t).get('stocks') or []
            except Exception as e:
                log('네이버 실패', market, page, repr(e)[:200]); break
            if page == 1: log('네이버', market, len(items), t[:150].replace('\n', ' '))
            for it in items:
                c = num(it.get('closePrice'))
                if c: rows[it.get('itemCode')] = {'c': c}
            if len(items) < 100: break
            time.sleep(0.1)
    return rows

def naver_one(code):
    for url, key in (('https://m.stock.naver.com/api/stock/%s/basic', 'closePrice'), ('https://polling.finance.naver.com/api/realtime/domestic/stock/%s', None)):
        try:
            t = http(url % code, headers={'Referer': 'https://m.stock.naver.com/'}); j = json.loads(t)
            c = num(j.get(key)) if key else num(((j.get('datas') or [{}])[0]).get('closePrice'))
            if c: return {'c': c}
            log('개별', code, t[:120])
        except Exception as e:
            log('개별 실패', code, repr(e)[:150])
    return None

rows, src = {}, ''
for name, fn in (('KRX', krx), ('네이버 금융', naver)):
    try: got = fn()
    except Exception as e: log(name, '예외', repr(e)[:200]); got = {}
    log(name, '종목 수', len(got))
    if len(got) >= 1000: rows, src = got, name; break

extra = [x.strip() for x in open('extra.txt').read().split('\n') if x.strip() and not x.startswith('#')] if os.path.exists('extra.txt') else []
for code in extra:
    if code not in rows and rows:
        r = naver_one(code)
        if r: rows[code] = r

os.makedirs('data', exist_ok=True)
if rows:
    out = {'at': kst.strftime('%Y-%m-%d %H:%M'), 'd': kst.strftime('%Y-%m-%d'), 'src': src, 'n': len(rows), 'rows': rows}
    json.dump(out, open('data/quotes.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    log('저장', out['at'], src, len(rows), '| 표본', {c: rows.get(c) for c in ('005930', '000660') + tuple(extra)})
else:
    log('받은 가격이 없어 quotes.json 을 바꾸지 않습니다.')
open('data/log.txt', 'w').write(kst.strftime('%Y-%m-%d %H:%M') + '\n' + '\n'.join(LOG) + '\n')
