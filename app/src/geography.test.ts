import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import worker from '../worker';
import { geographicResponse, publicGeographicIndex, validateGeographicIndex } from '../geography';
import { loadGeographicProfile, supportedGeographicCell, type GeographicProfile } from './geography';

const version = 'a'.repeat(64);
const data: GeographicProfile = { schema: 'birdahead-geographic-profile-v1', version, region: 'county', parent: 'state', species: { bird: [[1,1,0,0,'insufficient_support',1]] } };
const raw = Buffer.from(JSON.stringify(data));
const entry = {id:'county',name:'Synthetic county',kind:'county',parent:'state',key:`releases/geography/${version}/county.json`,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};
const index = {schema:'birdahead-geographic-index-v1' as const,version,public_noncommercial_eligible:true as const,attribution:'Synthetic',terms_url:'https://example.invalid',regions:[entry,{...entry,id:'state',name:'Synthetic state',kind:'state',parent:null,key:`releases/geography/${version}/state.json`}]};

test('public geographic response reads only active eligible allowlisted keys and verifies content',async()=>{
  let reads=0;
  const reader=async(key:string)=>{reads++;assert.equal(key,entry.key);return raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength) as ArrayBuffer;};
  assert.equal((await geographicResponse(index,version,'county',reader)).status,200);
  assert.equal(reads,1);
  assert.equal((await geographicResponse(index,version,'private',reader)).status,404);
  assert.equal((await geographicResponse(undefined,version,'county',reader)).status,404);
  assert.equal((await geographicResponse(index,'b'.repeat(64),'county',reader)).status,404);
  assert.equal(reads,1);
  assert.equal((await geographicResponse(index,version,'county',async()=>new ArrayBuffer(1))).status,503);
  assert.equal((await geographicResponse({...index,public_noncommercial_eligible:false},version,'county',reader)).status,404);
});
test('index omits private object keys and rejects unsafe fallback graphs',()=>{
  const publicIndex=publicGeographicIndex(validateGeographicIndex(index));
  assert.equal('key' in publicIndex.regions[0],false);
  assert.throws(()=>validateGeographicIndex({...index,regions:[{...entry,parent:'county'}]}));
  assert.throws(()=>validateGeographicIndex({...index,regions:[{...entry,key:'private/raw.tsv'}]}));
});
test('lazy retrieval fetches one requested region with anonymous immutable caching',async()=>{
  const publicIndex=publicGeographicIndex(index);let count=0;
  const fetcher=(async(url: string,init: RequestInit)=>{
    count++;assert.equal(url,`/api/public/geography/${version}/county`);assert.equal(init.credentials,'omit');assert.equal(init.cache,'force-cache');
    return new Response(raw);
  }) as typeof fetch;
  await Promise.all([loadGeographicProfile(publicIndex,'county',fetcher),loadGeographicProfile(publicIndex,'county',fetcher)]);
  assert.equal(count,1);
});
test('insufficient local support has an explicit parent, supported zero is retained',async()=>{
  const loaded:string[]=[];
  const result=await supportedGeographicCell(publicGeographicIndex(index),'county','bird',1,async id=>{
    loaded.push(id);return id==='county'?data:{...data,region:'state',parent:null,species:{bird:[[1,50,0,0,'supported',20]]}};
  });
  assert.deepEqual(loaded,['county','state']);assert.equal(result.effective_region,'state');assert.equal(result.cell?.[3],0);assert.equal(result.used_parent,true);
  const missing=await supportedGeographicCell(publicGeographicIndex(index),'county','unmapped',1,async()=>data);
  assert.equal(missing.cell,null);
});
test('Worker serves eligible geography anonymously only at the canonical host',async()=>{
  const reads:string[]=[];
  const env:any={APP_ORIGIN:'https://birdahead.com',DB:{prepare:()=>({first:async()=>({id:'geographic-worker-fixture',object_key:'fixture-catalog'})})},
    CONTENT:{get:async(key:string)=>{
      reads.push(key);
      return key==='fixture-catalog'?{json:async()=>({geography:index})}:{arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)};
    }}};
  const listing=await worker.request('https://birdahead.com/api/public/geography',{},env);
  assert.equal(listing.status,200);assert.equal((await listing.json() as any).regions.length,2);
  const response=await worker.request(`https://birdahead.com/api/public/geography/${version}/county`,{},env);
  assert.equal(response.status,200);assert.match(response.headers.get('Cache-Control')??'',/immutable/);
  assert.equal((await response.json() as any).region,'county');
  const before=reads.length;
  assert.equal((await worker.request(`https://birdahead.com/api/public/geography/${version}/raw`,{},env)).status,404);
  assert.equal((await worker.request(`https://preview.example/api/public/geography/${version}/county`,{},env)).status,404);
  assert.equal(reads.length,before);
});
