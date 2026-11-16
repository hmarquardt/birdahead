import { readFileSync, writeFileSync } from 'node:fs';

const d1 = process.env.BIRDAHEAD_D1_ID;
if (!d1 || !/^[a-f0-9-]{36}$/.test(d1)) throw new Error('BIRDAHEAD_D1_ID is required and must be a D1 UUID');
const source = readFileSync('wrangler.production.jsonc', 'utf8');
if (!source.includes('00000000-0000-0000-0000-000000000000')) throw new Error('Production config placeholder missing');
writeFileSync('wrangler.production.generated.jsonc', source.replace('00000000-0000-0000-0000-000000000000', d1));
console.log('Generated wrangler.production.generated.jsonc for dedicated D1', d1);
