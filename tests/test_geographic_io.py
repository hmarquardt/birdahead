import gzip
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tooling.discover import PRIVATE, save
from tooling.geography_io import Limits, Transfer, digest
from tooling.geographic_sources import unpack
from tooling.geographic_validation import compare
from tooling.geographic_release import compile_package


class Response(io.BytesIO):
    def __init__(self,data,headers,status=200):super().__init__(data);self.headers=headers;self.status=status


class GeographicIOTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=PRIVATE,prefix='test-geographic-io-'))
        self.limits=Limits(max_download_bytes=20,max_input_bytes=20,disk_reserve_bytes=1,max_spill_bytes=1)
    def tearDown(self):shutil.rmtree(self.root)
    def test_safe_exact_resume_and_checksum(self):
        t=Transfer({'example.invalid'},self.limits)
        target=self.root/'artifact.txt';part=self.root/'artifact.txt.part';part.write_bytes(b'abc')
        meta={'bytes':6,'etag':'"fixture"','accept_ranges':'bytes','content_type':'text/plain'}
        save(self.root/'artifact.txt.part.json',meta)
        def opened(url,method='GET',headers=None):
            if method=='HEAD':return Response(b'',{'Content-Length':'6','ETag':'"fixture"','Accept-Ranges':'bytes','Content-Type':'text/plain'})
            self.assertEqual(headers,{'Range':'bytes=3-','If-Range':'"fixture"'})
            return Response(b'def',{'ETag':'"fixture"','Content-Range':'bytes 3-5/6','Content-Type':'text/plain'},206)
        with patch.object(t,'open',side_effect=opened):
            result=t.download('https://example.invalid/signed?private=omitted',target)
        self.assertEqual(target.read_bytes(),b'abcdef');self.assertEqual(result['resumed_bytes'],3)
        self.assertNotIn('private',json.dumps(t.events))
    def test_unknown_size_oversize_challenge_and_changed_entities_fail(self):
        t=Transfer({'example.invalid'},self.limits);target=self.root/'artifact'
        with patch.object(t,'metadata',return_value={'bytes':None}):
            with self.assertRaises(ValueError):t.download('https://example.invalid/',target)
        with patch.object(t,'metadata',return_value={'bytes':21}):
            with self.assertRaises(ValueError):t.download('https://example.invalid/',target)
        with patch.object(t,'metadata',return_value={'bytes':6,'etag':None,'accept_ranges':None,'content_type':'text/html'}),patch.object(t,'open',return_value=Response(b'<html>',{'Content-Type':'text/html'})):
            with self.assertRaises(ValueError):t.download('https://example.invalid/',target)
        self.assertFalse(target.exists())
    def test_host_and_disk_guards(self):
        t=Transfer({'example.invalid'},self.limits)
        for url in ['http://example.invalid/','https://other.invalid/','https://secret@example.invalid/']:
            with self.assertRaises(ValueError):t.open(url)
        with patch('shutil.disk_usage',return_value=shutil._ntuple_diskusage(100,99,1)):
            with self.assertRaises(ValueError):self.limits.check_disk(self.root,1)
    def test_expansion_ceiling_preserves_no_partial_product(self):
        source=self.root/'source.gz'
        with gzip.open(source,'wb') as stream:stream.write(b'a'*21)
        with self.assertRaises(ValueError):unpack(source,self.root/'out.txt',self.limits)
        self.assertFalse((self.root/'out.txt').exists());self.assertFalse((self.root/'out.txt.part').exists())
    def test_source_unavailable_report_does_not_manufacture_frequency(self):
        p=self.root/'references';p.mkdir()
        save(p/'reference.json',{'metadata':{'sample_sizes':[2]*48},'rows':[]})
        report=compare(references=p)
        self.assertEqual(report['reference_samples'],96)
        self.assertEqual(report['historical_validation'],'blocked_source_unavailable')
        self.assertEqual(report['counties'],[])
    def test_synthetic_publication_always_rejected(self):
        p=self.root/'build';p.mkdir();save(p/'manifest.json',{'evidence':'synthetic_integration'})
        save(self.root/'decision.json',{});save(self.root/'validation.json',{})
        with self.assertRaises(ValueError):compile_package(p,self.root/'decision.json',self.root/'validation.json',self.root/'public')


if __name__=='__main__':unittest.main()
