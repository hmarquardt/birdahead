import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
from tooling.acquire import SafeClient,inat_license_info,license_info
from tooling.curation import rights_gate,photo_decision,duplicates


class AutomatedPolicyTests(unittest.TestCase):
    def test_noncommercial_rights_are_eligible_and_nd_is_not(self):
        asset={'creator':'Fixture creator','attribution':'Fixture credit','source_url':'https://example.org/record','source_record_id':'fixture','sha256':'a'*64,**inat_license_info('cc-by-nc')}
        self.assertTrue(rights_gate(asset)[0]);self.assertFalse(asset['commercial_compatible']);self.assertEqual(asset['license_version'],'4.0')
        asset.update(license_info('https://creativecommons.org/licenses/by-nc-nd/4.0/'));self.assertFalse(rights_gate(asset)[0])
    def test_deed_and_code_mismatch_rejected(self):
        asset={'creator':'Fixture','attribution':'credit','source_url':'https://example.org','source_record_id':'fixture','sha256':'a'*64,**inat_license_info('cc-by')}
        asset['license_url']='https://creativecommons.org/licenses/by-nc/4.0/'
        self.assertFalse(rights_gate(asset)[0])
    def test_model_confidence_alone_cannot_accept(self):
        asset={'species_code':'fixture','source_evidence':{'quality_grade':'research','concordant_non_owner_identifiers':[]},
               'technical_metrics':{'width':1024,'height':768,'edge_variance_256':100,'mean_luminance':128},
               'subject_screen':{'screen_passed':True,'localized_classification':{'margin':.1}}}
        result={'top_species':'fixture','source_rank':1,'all_cosines':{'fixture':.9},'top_margin':.8,'top5':[{'code':'fixture'}]}
        calibration={'parameters':{'fixture':{'min_cosine':.2,'min_margin':.015,'fitting_positive_count':3}}}
        passed,reasons=photo_decision(asset,result,result,calibration);self.assertFalse(passed);self.assertTrue(any('source identifier' in reason for reason in reasons))
        asset['source_evidence']['concordant_non_owner_identifiers']=['fixture-person']
        self.assertTrue(photo_decision(asset,result,result,calibration)[0])
        asset['subject_screen']['screen_passed']=False;self.assertFalse(photo_decision(asset,result,result,calibration)[0])
    def test_exact_and_perceptual_duplicate_flags(self):
        assets=[{'id':'one','kind':'photo','species_code':'fixture','sha256':'one','technical_metrics':{'dhash':'0000000000000000'}},
                {'id':'two','kind':'photo','species_code':'fixture','sha256':'two','technical_metrics':{'dhash':'0000000000000001'}}]
        duplicates(assets);self.assertTrue(assets[1]['duplicate_flags'])
    def test_xc_exception_and_logs_do_not_reveal_url_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret='fixture-never-print-this-key'
            error=urllib.error.HTTPError('https://xeno-canto.org/api/3/recordings?key='+secret,403,'request '+secret,{},io.BytesIO(b''))
            client=SafeClient(budget=1)
            with patch('tooling.acquire.WORK',Path(tmp)),patch('tooling.acquire.credential',return_value=secret),patch('urllib.request.urlopen',side_effect=error):
                with self.assertRaises(RuntimeError) as caught:client.json('https://xeno-canto.org/api/3/recordings',{'query':'grp:birds'},xc=True)
            self.assertNotIn(secret,str(caught.exception));self.assertNotIn(secret,json.dumps(client.events));self.assertNotIn('key=',json.dumps(client.events))


if __name__=='__main__':unittest.main()
