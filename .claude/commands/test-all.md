---
description: Run every test suite (JS harnesses + backend pytest) and the inline-JS parse check
---
Run, in this order, and report each result:

1. `node tests/zones.test.js` (zone logic + geo golden fixture)
2. `node tests/sched.test.js` (scheduling pure helpers)
3. In `backend/`: `python -m pytest tests/ -q` (optimizer, sequencing, batch, geo parity, cache, auth — ~2-4 min)
4. Inline-JS parse check:
   `node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');let ok=true;[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m,i)=>{try{new Function(m[1])}catch(e){ok=false;console.error(i,e.message)}});console.log(ok?'parse OK':'FAIL');process.exit(ok?0:1)"`

All four must be green before claiming any engine change is done (verification-before-completion). If anything fails, apply superpowers:systematic-debugging — do not patch blind.
