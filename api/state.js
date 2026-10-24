// 오늘 뭐 먹지 — 투표·후기·추가한 집을 저장하는 서버 함수 (Vercel Serverless Function)
// 저장소: Upstash Redis (Vercel Storage에서 연결하면 환경변수가 자동으로 들어옵니다)
const crypto = require('crypto');

const REDIS_URL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const REDIS_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;

async function redis(cmds) {
  const r = await fetch(REDIS_URL.replace(/\/$/, '') + '/pipeline', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + REDIS_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify(cmds),
  });
  if (!r.ok) throw new Error('storage_' + r.status);
  const out = await r.json();
  return out.map((x) => {
    if (x && x.error) throw new Error(x.error);
    return x ? x.result : null;
  });
}

function hashToObj(arr, parse) {
  const o = {};
  for (let i = 0; arr && i < arr.length; i += 2) {
    if (!parse) { o[arr[i]] = arr[i + 1]; continue; }
    try { o[arr[i]] = JSON.parse(arr[i + 1]); } catch (e) { /* skip broken row */ }
  }
  return o;
}

async function readAll() {
  const [v, r, e, u] = await redis([
    ['HGETALL', 'votes'], ['HGETALL', 'reviews'], ['HGETALL', 'extra'], ['HGETALL', 'users'],
  ]);
  return { ok: true, votes: hashToObj(v, true), reviews: hashToObj(r, true), extra: hashToObj(e, true), users: hashToObj(u, false) };
}

const sha = (s) => crypto.createHash('sha256').update(String(s)).digest('hex');
function fail(code, msg) { const err = new Error(msg); err.status = code; return err; }
function sized(obj, max) {
  const s = JSON.stringify(obj || {});
  if (s.length > max) throw fail(413, 'too_large');
  return s;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (!REDIS_URL || !REDIS_TOKEN) {
    res.status(503).json({ ok: false, error: 'storage_not_configured' });
    return;
  }
  try {
    if (req.method === 'GET') { res.status(200).json(await readAll()); return; }
    if (req.method !== 'POST') { res.status(405).json({ ok: false, error: 'method' }); return; }

    let b = req.body;
    if (typeof b === 'string') { try { b = JSON.parse(b); } catch (e) { b = {}; } }
    b = b || {};
    const uid = String(b.uid || '');
    const key = String(b.key || '');
    if (!/^u[0-9a-f]{16}$/.test(uid) || !/^[0-9a-f]{32}$/.test(key)) throw fail(400, 'bad_id');

    // 기기마다 만든 비밀키로 본인 확인 (처음 쓸 때 등록)
    const [stored] = await redis([['HGET', 'auth', uid]]);
    if (stored && stored !== sha(key)) throw fail(403, 'forbidden');

    const cmds = [];
    if (!stored) cmds.push(['HSETNX', 'auth', uid, sha(key)]);
    const name = String(b.name || '').replace(/[<>]/g, '').trim().slice(0, 12);
    if (name) cmds.push(['HSET', 'users', uid, name]);

    const op = b.op;
    if (op === 'vote') {
      cmds.push(['HSET', 'votes', uid, sized(b.doc, 4000)]);
    } else if (op === 'reviews') {
      cmds.push(['HSET', 'reviews', uid, sized(b.doc, 80000)]);
    } else if (op === 'extra') {
      const id = String(b.id || '');
      if (!/^x[0-9a-z]{4,20}$/.test(id)) throw fail(400, 'bad_place_id');
      const p = Object.assign({}, b.place || {}, { by: uid, custom: 1 });
      cmds.push(['HSET', 'extra', id, sized(p, 3000)]);
    } else if (op === 'extra_del') {
      const id = String(b.id || '');
      const [cur] = await redis([['HGET', 'extra', id]]);
      if (cur) {
        let p = {};
        try { p = JSON.parse(cur); } catch (e) { /* ignore */ }
        if (p.by && p.by !== uid) throw fail(403, 'not_owner');
      }
      cmds.push(['HDEL', 'extra', id]);
    } else if (op !== 'hello') {
      throw fail(400, 'bad_op');
    }
    if (cmds.length) await redis(cmds);
    res.status(200).json(await readAll());
  } catch (e) {
    res.status(e.status || 500).json({ ok: false, error: String(e.message || e) });
  }
};
