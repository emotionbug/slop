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

if __name__=='__main__': unittest.main()
