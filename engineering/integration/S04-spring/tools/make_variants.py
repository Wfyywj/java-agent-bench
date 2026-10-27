from pathlib import Path
import shutil,json
R=Path(__file__).resolve().parents[1]
def variant(name,file,old,new):
 d=R/name/'src';shutil.copytree(R/'reference/src',d,dirs_exist_ok=True)
 p=d/'bench'/file;s=p.read_text();assert old in s;p.write_text(s.replace(old,new,1))
entry='    @Transactional(rollbackFor=BusinessFailure.class)\n    public void cancel(int batch)'
variant('baseline','BatchService.java',entry,'    public void cancel(int batch)')
variant('mutants/self-invocation','BatchService.java',entry,'    public void cancel(int batch)')
variant('mutants/default-checked-policy','BatchService.java',entry,'    @Transactional\n    public void cancel(int batch)')
variant('mutants/swallow-checked','BatchService.java','        cancelInside(batch);','        try { cancelInside(batch); } catch (BusinessFailure ignored) {}')
variant('mutants/double-release','BatchService.java','            if (order.state().equals("CANCELLED")) continue;','            if (order.state().equals("CANCELLED")) { orders.release(order,probe); continue; }')
variant('mutants/allow-delivered','BatchService.java','            if (order.state().equals("DELIVERED")) throw new BusinessFailure("Already delivered");','            if (order.state().equals("DELIVERED")) continue;')
variant('mutants/lost-update','OrderRepository.java','available=available+? where sku=?",order.quantity()','available=? where sku=?",available+order.quantity()')
variant('mutants/no-batch-lock','OrderRepository.java',' where id=? for update',' where id=?')
variant('mutants/global-lock','OrderRepository.java','        jdbc.queryForObject("select id from batches where id=? for update", Integer.class, batch);','        jdbc.queryForList("select id from batches order by id for update", Integer.class);')
variant('mutants/early-return-cancelled','BatchService.java','            if (order.state().equals("CANCELLED")) continue;','            if (order.state().equals("CANCELLED")) return;')
variant('mutants/early-return-delivered','BatchService.java','            if(order.state().equals("DELIVERED")) continue;','            if(order.state().equals("DELIVERED")) return;')
files=[{'source':'baseline/'+str(p.relative_to(R/'baseline')), 'target':str(p.relative_to(R/'baseline'))} for p in sorted((R/'baseline/src').rglob('*.java'))]
files.append({'source':'PROMPT.md','target':'PROMPT.md'})
(R/'agent-files.json').write_text(json.dumps({'schema_version':1,'files':files},indent=2)+'\n')
