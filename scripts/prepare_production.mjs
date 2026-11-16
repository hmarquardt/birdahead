import { readFileSync, writeFileSync } from 'node:fs';

const d1 = process.env.BIRDAHEAD_D1_ID;
if (!d1 || !/^[a-f0-9-]{36}$/.test(d1)) throw new Error('BIRDAHEAD_D1_ID is required and must be a D1 UUID');
const source = readFileSync('wrangler.production.jsonc', 'utf8');
const databaseId = /("database_id"\s*:\s*")[^"]+(")/;
if (!databaseId.test(source)) throw new Error('Production D1 database_id missing');
writeFileSync('wrangler.production.generated.jsonc', source.replace(databaseId, `$1${d1}$2`));
console.log('Generated wrangler.production.generated.jsonc for dedicated D1', d1);
