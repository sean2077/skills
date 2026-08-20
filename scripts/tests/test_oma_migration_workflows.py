#!/usr/bin/env python3
"""Behavioral regressions for migrated deterministic workflow runtimes."""
from __future__ import annotations
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from typing import Any, Dict, Optional

ROOT=Path(__file__).resolve().parents[2]
AUTO=ROOT/'skills/autopilot/scripts/autopilot_state.py'
INTERVIEW=ROOT/'skills/deep-interview/scripts/interview_state.py'
RALPH=ROOT/'skills/ralph/scripts/ralph_state.py'

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Path(self.tmp.name)/'repo'; self.repo.mkdir()
        self.git('init','-q'); self.git('config','user.name','Test'); self.git('config','user.email','t@example.invalid')
        (self.repo/'seed').write_text('x\n'); self.git('add','seed'); self.git('commit','-qm','seed')
    def tearDown(self): self.tmp.cleanup()
    def git(self,*args,cwd:Optional[Path]=None):
        return subprocess.run(['git',*args],cwd=cwd or self.repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=20).stdout.strip()
    def cli(self,script:Path,*args,cwd:Optional[Path]=None,rc=0)->Dict[str,Any]:
        cp=subprocess.run([sys.executable,str(script),*args],cwd=cwd or self.repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
        self.assertEqual(cp.returncode,rc,msg=f'out={cp.stdout}\nerr={cp.stderr}')
        raw=cp.stdout.strip() or cp.stderr.strip(); self.assertTrue(raw)
        return json.loads(raw.splitlines()[-1])
    def jf(self,name,payload):
        path=self.repo/name; path.write_text(json.dumps(payload)); return path

    def test_autopilot_success_and_retry_terminal(self):
        o=self.cli(AUTO,'start','--id','ship','--goal','ship'); self.assertEqual(o['state']['phase'],'clarify')
        self.cli(AUTO,'advance','--id','ship','--expected-revision','1','--to','plan')
        self.cli(AUTO,'plan','--id','ship','--expected-revision','2','--path','plan.md')
        self.cli(AUTO,'advance','--id','ship','--expected-revision','3','--to','verify')
        o=self.cli(AUTO,'verify','--id','ship','--expected-revision','4','--exit-code','0','--summary','green'); self.assertEqual(o['state']['phase'],'deliver')
        o=self.cli(AUTO,'finish','--id','ship','--expected-revision','5'); self.assertEqual(o['state']['status'],'done')
        self.cli(AUTO,'start','--id','retry','--goal','bounded')
        self.cli(AUTO,'advance','--id','retry','--expected-revision','1','--to','plan')
        self.cli(AUTO,'plan','--id','retry','--expected-revision','2','--path','p.md')
        self.cli(AUTO,'advance','--id','retry','--expected-revision','3','--to','verify')
        o=self.cli(AUTO,'verify','--id','retry','--expected-revision','4','--exit-code','1','--summary','one'); self.assertEqual(o['state']['phase'],'implement')
        self.cli(AUTO,'advance','--id','retry','--expected-revision','5','--to','verify')
        o=self.cli(AUTO,'verify','--id','retry','--expected-revision','6','--exit-code','1','--summary','two',rc=4); self.assertEqual(o['state']['status'],'blocked')

    def test_revision_cas(self):
        self.cli(AUTO,'start','--id','cas','--goal','safe')
        o=self.cli(AUTO,'advance','--id','cas','--expected-revision','0','--to','plan',rc=5); self.assertEqual(o['error'],'revision_conflict')

    def test_interview_topology_score_complete(self):
        o=self.cli(INTERVIEW,'start','--id','idea','--idea','api','--depth','deep'); self.assertEqual(o['metrics']['next_target'],'problem')
        topo=self.jf('topo.json',{'schema':'agent-interview-topology/1','components':[{'id':'api','name':'API','description':'surface','status':'active','evidence':['request']},{'id':'worker','name':'Worker','description':'background surface','status':'active','evidence':['request']},{'id':'ui','name':'UI','description':'later','status':'deferred','evidence':[]}],'deferrals':[{'component_id':'ui','reason':'later'}]})
        o=self.cli(INTERVIEW,'topology','--id','idea','--expected-revision','1','--input',str(topo))
        scores={k:1.0 for k in o['state']['dimensions']}
        component_scores={'api':scores,'worker':scores}
        rnd=self.jf('round.json',{'schema':'agent-interview-round/1','round':1,'target':{'component':'api','dimension':'problem'},'question':'What problem?','answer':'[from-user] latency','component_scores':component_scores,'evidence':{k:['evidence'] for k in scores}})
        o=self.cli(INTERVIEW,'score','--id','idea','--expected-revision','2','--input',str(rnd)); self.assertTrue(o['metrics']['gate_passed'])
        o=self.cli(INTERVIEW,'complete','--id','idea','--expected-revision','3','--spec-path','spec.md'); self.assertEqual(o['state']['status'],'completed')

    def test_interview_scores_every_active_component_and_uses_dimension_minimum(self):
        self.cli(INTERVIEW,'start','--id','multi','--idea','service','--depth','deep')
        topo=self.jf('multi-topo.json',{'schema':'agent-interview-topology/1','components':[{'id':'api','name':'API','description':'surface','status':'active','evidence':['request']},{'id':'worker','name':'Worker','description':'background surface','status':'active','evidence':['request']},{'id':'later','name':'Later','description':'deferred surface','status':'deferred','evidence':[]}],'deferrals':[{'component_id':'later','reason':'later'}]})
        o=self.cli(INTERVIEW,'topology','--id','multi','--expected-revision','1','--input',str(topo))
        dims=o['state']['dimensions']; good={k:1.0 for k in dims}; weak=dict(good); weak['problem']=0.4
        rnd=self.jf('multi-round.json',{'schema':'agent-interview-round/1','round':1,'target':{'component':'api','dimension':'problem'},'question':'What problem?','answer':'[from-user] latency','component_scores':{'api':good,'worker':weak},'evidence':{'api':{k:['api evidence'] for k in dims},'worker':{k:['worker evidence'] for k in dims}}})
        o=self.cli(INTERVIEW,'score','--id','multi','--expected-revision','2','--input',str(rnd))
        self.assertEqual(o['state']['component_scores']['worker']['problem'],0.4)
        self.assertEqual(o['metrics']['dimension_scores']['problem'],0.4)
        self.assertFalse(o['metrics']['gate_passed'])
        self.assertEqual(o['metrics']['next_target'],{'component':'worker','dimension':'problem'})

    def test_malformed_state_fails_closed(self):
        cases=[(AUTO,'autopilot',['start','--id','broken-auto','--goal','safe']), (INTERVIEW,'deep-interview',['start','--id','broken-interview','--idea','safe']), (RALPH,'ralph',['start','--id','broken-ralph','--goal','safe'])]
        for script, workflow, start_args in cases:
            self.cli(script,*start_args)
            path=self.repo/'.agent-workflows'/workflow/(start_args[start_args.index('--id')+1]+'.json')
            path.write_text(json.dumps({'schema':f'agent-workflow/{workflow}/1','workflow':workflow,'id':path.stem,'revision':1}))
            o=self.cli(script,'status','--id',path.stem,rc=6)
            self.assertEqual(o['error'],'corrupt_state')

    def test_read_only_status_does_not_create_state_root(self):
        for script, workflow in [(AUTO,'autopilot'),(INTERVIEW,'deep-interview'),(RALPH,'ralph')]:
            o=self.cli(script,'status','--id','missing-'+workflow,rc=3)
            self.assertEqual(o['error'],'not_found')
            self.assertFalse((self.repo/'.agent-workflows'/workflow).exists())

    def test_interview_rejects_duplicate_component(self):
        self.cli(INTERVIEW,'start','--id','bad','--idea','x')
        topo=self.jf('bad.json',{'schema':'agent-interview-topology/1','components':[{'id':'same','name':'A','description':'a','status':'active','evidence':[]},{'id':'same','name':'B','description':'b','status':'active','evidence':[]}],'deferrals':[]})
        o=self.cli(INTERVIEW,'topology','--id','bad','--expected-revision','1','--input',str(topo),rc=2); self.assertEqual(o['error'],'invalid_topology')

    def test_ralph_pass_stall_plateau_exhaust(self):
        self.cli(RALPH,'start','--id','pass','--goal','green','--max-rounds','2'); self.cli(RALPH,'next','--id','pass','--expected-revision','1')
        o=self.cli(RALPH,'check','--id','pass','--expected-revision','2','--round','1','--verifier-exit','0'); self.assertEqual(o['state']['status'],'passed')
        self.cli(RALPH,'start','--id','stall','--goal','fix','--max-rounds','5','--stall-window','2')
        self.cli(RALPH,'next','--id','stall','--expected-revision','1'); self.cli(RALPH,'check','--id','stall','--expected-revision','2','--round','1','--verifier-exit','1','--signature','same')
        self.cli(RALPH,'next','--id','stall','--expected-revision','3'); o=self.cli(RALPH,'check','--id','stall','--expected-revision','4','--round','2','--verifier-exit','1','--signature','same',rc=4); self.assertEqual(o['state']['status'],'stalled')
        self.cli(RALPH,'start','--id','plateau','--goal','score','--max-rounds','5','--stall-window','5','--keep-policy','score-improvement','--plateau-window','2')
        rev=1
        for n in (1,2,3):
            self.cli(RALPH,'next','--id','plateau','--expected-revision',str(rev)); rev+=1
            o=self.cli(RALPH,'check','--id','plateau','--expected-revision',str(rev),'--round',str(n),'--verifier-exit','1','--signature',f's{n}','--score','0.5',rc=4 if n==3 else 0); rev+=1
        self.assertEqual(o['state']['status'],'plateaued')
        self.cli(RALPH,'start','--id','budget','--goal','one','--max-rounds','1'); self.cli(RALPH,'next','--id','budget','--expected-revision','1')
        o=self.cli(RALPH,'check','--id','budget','--expected-revision','2','--round','1','--verifier-exit','1','--signature','left',rc=4); self.assertEqual(o['state']['status'],'exhausted')

    def test_shared_worktree_binding_and_rebind(self):
        self.cli(RALPH,'start','--id','owner','--goal','bind')
        other=Path(self.tmp.name)/'other'; self.git('worktree','add','-qb','other',str(other))
        o=self.cli(RALPH,'status','--id','owner',cwd=other,rc=5); self.assertFalse(o['binding']['ok'])
        o=self.cli(RALPH,'rebind','--id','owner','--expected-revision','1',cwd=other); self.assertEqual(o['state']['binding']['worktree'],str(other.resolve()))

    @unittest.skipIf(os.name=='nt','symlink privileges vary on Windows')
    def test_symlinked_state_base_rejected(self):
        outside=Path(self.tmp.name)/'outside'; outside.mkdir(); (self.repo/'.agent-workflows').symlink_to(outside,target_is_directory=True)
        o=self.cli(RALPH,'start','--id','unsafe','--goal','reject',rc=6); self.assertEqual(o['error'],'unsafe_state_root'); self.assertFalse((outside/'ralph').exists())

if __name__=='__main__': unittest.main()
