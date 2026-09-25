import copy,importlib.util,os,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('policy',Path(__file__).resolve().parents[1]/'symbol-policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)

def symbol(name,defined=False,binding='GLOBAL'):
 return dict(name=name,defined=defined,binding=binding,visibility='DEFAULT')
def elf(path,owner,**extra):
 value=dict(resolved_path=path,rpm_owner=dict(packages=[owner] if owner else []),needed=[],search_paths=[],copy_relocations=[],target_symbols=[],machine='x86_64')
 value['class']='ELF64';value.update(extra);return value

class PolicyTests(unittest.TestCase):
 def classify(self,match,infos,changed=None,outgoing=None,owners=None,incoming=None):
  audit=dict(audit_version=3,direct_import_matches=[match],symbols_checked=['free','calloc','gone'],errors=[],directory_symlinks_outside_roots=[])
  removals=dict(removed_sonames=['libold.so.1'],libraries=[dict(library='/usr/lib64/libgvpr.so.2',scan_symbols=['free','calloc'])])
  with patch.object(policy.DETAILS,'elf_details',side_effect=lambda p,s:copy.deepcopy(infos[p])),patch.object(policy.DETAILS,'cached_libraries',return_value={}),patch.object(policy.DETAILS,'dependency_candidates',return_value=(['/test/libc.so.6'],[])),patch.dict(os.environ,{},clear=True):
   return policy.classify(audit,removals,changed or set(),outgoing or {},owners or set(),incoming)
 def fixtures(self):
  match=dict(path='/test/app',aliases=['/test/app'],symbols=['calloc'],removed_needed=[])
  infos={'/test/app':elf('/test/app','app',needed=['libc.so.6'],target_symbols=[symbol('calloc@GLIBC_2.2.5')]),'/test/libc.so.6':elf('/test/libc.so.6','glibc',soname='libc.so.6',target_symbols=[symbol('calloc@@GLIBC_2.2.5',True,'WEAK')])}
  return match,infos
 def test_exact_versioned_weak_provider(self):
  m,i=self.fixtures();self.assertTrue(self.classify(m,i)['allow_transaction'])
  i['/test/libc.so.6']['target_symbols'][0]['name']='calloc@@GLIBC_2.34'
  self.assertFalse(self.classify(m,i)['allow_transaction'])
 def test_changed_provider_is_not_cleared(self):
  m,i=self.fixtures();self.assertFalse(self.classify(m,i,changed={'/test/libc.so.6'})['allow_transaction'])
 def test_removed_soname_blocks_manual_consumer(self):
  m,i=self.fixtures();m['removed_needed']=['libold.so.1'];self.assertFalse(self.classify(m,i)['allow_transaction'])
 def test_replacement_requires_all_owned_aliases_and_new_imports(self):
  m,i=self.fixtures();m['symbols']=['gone'];m['removed_needed']=['libold.so.1'];i['/test/app']['target_symbols']=[symbol('gone')]
  new={'/test/app':elf('/test/app',None)}
  kw=dict(changed={'/test/app'},outgoing={'/test/app':0},owners={'app'},incoming=new)
  self.assertTrue(self.classify(m,i,**kw)['allow_transaction'])
  new['/test/app']['needed']=['libold.so.1'];self.assertFalse(self.classify(m,i,**kw)['allow_transaction'])
  new['/test/app']['needed']=[];new['/test/app']['target_symbols']=[symbol('gone')];self.assertFalse(self.classify(m,i,**kw)['allow_transaction'])
  new['/test/app']['target_symbols']=[];m['aliases'].append('/test/unowned-hardlink');self.assertFalse(self.classify(m,i,**kw)['allow_transaction'])

if __name__=='__main__':unittest.main()
