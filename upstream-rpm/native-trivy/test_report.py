import copy
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('report',Path(__file__).with_name('report.py'))
report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)

class VendorReviewTests(unittest.TestCase):
    def test_exact_fixed_module_context_only(self):
        reviews=json.loads(Path(__file__).with_name('vendor-reviews.json').read_text())['reviews']
        review=reviews[0]
        finding={'PkgName':review['package'],'InstalledVersion':review['installed_version'],'VulnerabilityID':review['cve']}
        result={'Type':'redhat','Packages':[{'Name':review['package'],'Epoch':0,'Version':review['version'],
            'Release':review['release'],'Arch':'x86_64','Maintainer':'Red Hat, Inc.'}]}
        os_info={'Family':'redhat','Name':'8.10'}
        self.assertEqual(report.vendor_review(finding,result,os_info,reviews),review)
        for key,value in [('InstalledVersion','1.641-9.module+el8.10.0+24875+bc962974'),('VulnerabilityID','CVE-OTHER')]:
            changed=dict(finding);changed[key]=value
            self.assertIsNone(report.vendor_review(changed,result,os_info,reviews))
        for key,value in [('Arch','i686'),('Maintainer','Linux OSS local build'),('Release','different')]:
            changed=copy.deepcopy(result);changed['Packages'][0][key]=value
            self.assertIsNone(report.vendor_review(finding,changed,os_info,reviews))
        self.assertIsNone(report.vendor_review(finding,result,{'Family':'redhat','Name':'9.6'},reviews))
        mixed=copy.deepcopy(result);other=dict(mixed['Packages'][0]);other['Arch']='i686';mixed['Packages'].append(other)
        self.assertIsNone(report.vendor_review(finding,mixed,os_info,reviews))

if __name__=='__main__':unittest.main()
