// 오늘 뭐 먹지 — 이용량 집계 (방문 기록 + 통계 조회)
// POST: 화면을 열 때 한 번 호출 → 날짜별 방문자 수(중복 제거)·열람 수·근무지별 열람 수를 올립니다.
// GET : 최근 30일 날짜별 숫자와 전체 누적 숫자를 돌려줍니다. 이름·후기 내용은 내보내지 않습니다.
const REDIS_URL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const REDIS_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
const SITES = ['sejong', 'banpo', 'yeouido', 'seoul'];
const KEEP = 60 * 60 * 24 * 120; // 날짜별 기록은 120일 보관

async function redis(cmds) {
  const r = await fetch(REDIS_URL.replace(/\/$/, '') + '/pipeline', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + REDIS_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify(cmds),
  });
  if (!r.ok) throw new Error('storage_' + r.status);
  return (await r.json()).map((x) => (x && !x.error ? x.result : null));
}

// 한국 시간 기준 날짜 (YYYY-MM-DD)
function kstDate(offsetDays) {
  return new Date(Date.now() + 9 * 3600e3 - (offsetDays || 0) * 86400e3).toISOString().slice(0, 10);
}

function hashToObj(arr) {
  const o = {};
  for (let i = 0; arr && i < arr.length; i += 2) o[arr[i]] = Number(arr[i + 1]) || 0;
  return o;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (!REDIS_URL || !REDIS_TOKEN) { res.status(503).json({ ok: false, error: 'storage_not_configured' }); return; }
  try {
    if (req.method === 'POST') {
      let b = req.body;
      if (typeof b === 'string') { try { b = JSON.parse(b); } catch (e) { b = {}; } }
      b = b || {};
      const vid = String(b.vid || '');
      if (!/^u[0-9a-f]{16}$/.test(vid)) { res.status(400).json({ ok: false, error: 'bad_id' }); return; }
      const site = SITES.includes(b.site) ? b.site : 'other';
      const org = String(b.org || '').replace(/[<>"'&]/g, '').trim().slice(0, 20); // 세종 사무실(부처) 이름
      const d = kstDate();
      await redis([
        ['PFADD', 'st:vis:' + d, vid], ['EXPIRE', 'st:vis:' + d, KEEP],
        ['PFADD', 'st:vis:all', vid],
        ['HINCRBY', 'st:view', d, 1],
        ['HINCRBY', 'st:site:' + d, site, 1], ['EXPIRE', 'st:site:' + d, KEEP],
      ].concat(org ? [['HINCRBY', 'st:org:' + d, org, 1], ['EXPIRE', 'st:org:' + d, KEEP]] : []));
      res.status(200).json({ ok: true });
      return;
    }
    if (req.method !== 'GET') { res.status(405).json({ ok: false, error: 'method' }); return; }

    const days = [];
    for (let i = 29; i >= 0; i--) days.push(kstDate(i));
    const cmds = [['PFCOUNT', 'st:vis:all'], ['HGETALL', 'st:view'], ['HLEN', 'users'], ['HLEN', 'votes'],
      ['HGETALL', 'reviews'], ['HLEN', 'extra']];
    days.forEach((d) => cmds.push(['PFCOUNT', 'st:vis:' + d], ['PFCOUNT', 'st:act:' + d], ['HGETALL', 'st:act:n:' + d], ['HGETALL', 'st:site:' + d], ['HGETALL', 'st:org:' + d]));
    const out = await redis(cmds);
    const [visAll, viewArr, nUsers, nVoters, revArr, nExtra] = out;
    const views = hashToObj(viewArr);

    // 후기: 사람 수 / 후기 수 / 폐업 신고 수 (내용은 세지 않고 개수만)
    let reviewers = 0, reviewItems = 0, goneReports = 0;
    for (let i = 0; revArr && i < revArr.length; i += 2) {
      try {
        const doc = JSON.parse(revArr[i + 1]) || {};
        const n = Object.keys(doc.items || {}).length;
        if (n) reviewers += 1;
        reviewItems += n;
        goneReports += Object.keys(doc.gone || {}).length;
      } catch (e) { /* skip */ }
    }

    const daily = days.map((d, i) => {
      const base = 6 + i * 5;
      return { date: d, visitors: out[base] || 0, views: views[d] || 0, active: out[base + 1] || 0,
        actions: hashToObj(out[base + 2]), sites: hashToObj(out[base + 3]), orgs: hashToObj(out[base + 4]) };
    });
    res.status(200).json({
      ok: true,
      now: new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 16).replace('T', ' ') + ' (KST)',
      total: {
        visitors: visAll || 0,
        views: Object.values(views).reduce((a, b) => a + b, 0),
        nicknames: nUsers || 0, voters: nVoters || 0, reviewers, reviews: reviewItems, goneReports, addedPlaces: nExtra || 0,
      },
      daily,
    });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e.message || e) });
  }
};
