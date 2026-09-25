import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('feed', Path(__file__).with_name('refresh-feed.py'))
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

class FeedTests(unittest.TestCase):
    def test_product_identity_and_negation(self):
        cve = {'id':'CVE-TEST','configurations':[{'operator':'AND','negate':True,'nodes':[{'cpeMatch':[
            {'vulnerable':True,'criteria':'cpe:2.3:a:gnu:tar:*:*:*:*:*:*:*:*','versionEndExcluding':'1.36'},
            {'vulnerable':True,'criteria':'cpe:2.3:a:node-tar:tar:*:*:*:*:*:*:*:*'},
            {'vulnerable':False,'criteria':'cpe:2.3:a:gnu:tar:*:*:*:*:*:*:*:*'}]}]}]}
        result=feed.normalize(cve,{'part':'a','vendor':'gnu','product':'tar'})
        self.assertEqual(len(result['matches']),1)
        self.assertTrue(result['matches'][0]['conditional'])
        self.assertTrue(result['matches'][0]['negated'])
        self.assertEqual(result['matches'][0]['versionEndExcluding'],'1.36')

    def test_environment_cpe_is_not_a_vulnerable_product(self):
        alias={'part':'a','vendor':'sqlite','product':'sqlite'}
        cve={'id':'CVE-ENV','configurations':[{'operator':'AND','nodes':[{'cpeMatch':[
            {'vulnerable':True,'criteria':'cpe:2.3:a:php:php:*:*:*:*:*:*:*:*'},
            {'vulnerable':False,'criteria':'cpe:2.3:a:sqlite:sqlite:*:*:*:*:*:*:*:*'}]}]}]}
        self.assertTrue(feed.normalize(cve,alias)['context_only'])
        self.assertFalse(feed.normalize({'id':'CVE-MISSING'},alias)['context_only'])
        cve['configurations'][0]['nodes'][0]['cpeMatch'][1]['vulnerable']=True
        self.assertFalse(feed.normalize(cve,alias)['context_only'])

if __name__=='__main__': unittest.main()
