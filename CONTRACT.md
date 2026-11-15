# 隔离修正分支维护契约

## 仓库与现状
python3 seed_repo.py 在 repo/ 构造真实 Git 仓库，停在 quarantine-replay。
共同祖先、入仓热修复和回放原分支分别由 baseline/base、baseline/hotfix、
baseline/replay 三个标签固定；分支名为 ingest-idempotency、quarantine-replay。
构造器重复运行只检查标签，不覆盖工作区或重置提交。scaffold/ 是只读题源材料。
两个分支分别修改 warehouse.py 和 docs/maintenance.md，存在真实文本及语义冲突。
热修复分支保护原始记录重投；回放分支允许修正但事故重试会重复入账。
本轮须完成兼容合并，不以只诊断或只写未来修复建议代替合并。

## 已有入口与数据
在 repo/ 下运行 Python 入口。Warehouse(path).accept(record,payload,attempt=None)
处理原始输入；original_receipt(record) 返回原始持久回执，找不到返回 None。
payload 是且仅是 {"station":非空字符串,"value":非布尔整数}；value 可负。
record 为非空字符串。修正入口 replay.apply(w,q,record,attempt,payload,
hook=...,lose_response=False)，attempt 是非空字符串，在 record 内标识尝试。
q 是隔离 SQLite 路径，w 是入仓 SQLite 路径，两者不同。
Queue(q).add(record,reason) 为该记录建待办；record 必须已有待办才可修正。
本题只用一个进程串行运行，不要求多工作者、部署、旧库批量结构迁移。
允许增加内部持久结构和查询，但不改变现有入口、原回执及样例的含义。
不得合并两个数据库，不得使用 ATTACH 或跨库原子事务。

Warehouse.rows() 输出按 seq 排序的字典列表，每项含
seq、record、attempt、payload、digest、receipt；原始记录 attempt 为 None。
digest 是 payload 按 sort_keys=True,separators=(",",":"),ensure_ascii=False
序列化后 UTF-8 字节的 SHA-256。原始回执恰为 {"seq":整数,"record":字符串,"digest":字符串}；
修正回执至少保留这三个字段，可增补绑定信息。回执不得重新生成另一 seq。
Queue.rows() 按 record 排序，公开 record、reason、state、attempt、payload、receipt。
state 为 open/sending/closed；可增加内部状态，最终公开语义不变。
成果是追加修订账：每个原始输入及每个成功修正各保留一条，不覆盖旧修订。

## 本轮必须满足的业务行为
原始输入同号同内容重投返回原回执且不增加成果，同号异内容抛 ValueError。
同一记录的新尝试只在上一尝试结案后接纳；首个尝试可以来自 open 待办。
首次持久接纳修正后，record、attempt、payload 的绑定冻结，包括尚未发送完成的尝试。
相同尝试同内容重放返回该尝试的原持久入仓回执且只入账一次；同号异内容抛 ValueError，两个库均不得因此改变。
同一记录后续尝试使用新 attempt，各自入账；已结案旧尝试重投返回旧回执，不覆盖当前任务及后续尝试的结案依据。
不同 record 可以使用相同 attempt 文本，且 attempt 文本可等于 record，不能与原始输入身份相撞。
隔离结案必须引用该 record、attempt、payload 对应的持久入仓回执，发送记录本身不能作为结案证据。
入仓已提交但响应丢失，或任一交接边界进程退出，原请求重新运行须完成同一尝试的交接，不得误结案或重复入账。
必须保留原始入仓回执的内容和 original_receipt(record) 的兼容读取。
对待办不存在、载荷非法、未结案时发起另一新尝试，须抛 ValueError 且不改变两库。
实际合并须选择并说明历史修正身份与回执的持久归属、未决交接的恢复判据，不能只把重试变成新的尝试。

## 可重跑入口与样例
python3 runner.py ingest --warehouse w.db --queue q.db --record r1 --payload '{"station":"S1","value":10}'
python3 runner.py quarantine --warehouse w.db --queue q.db --record r1 --reason outlier
python3 runner.py replay --warehouse w.db --queue q.db --record r1 --attempt t1 --payload '{"station":"S1","value":13}'
python3 runner.py snapshot --warehouse w.db --queue q.db
前三次首次调用退出 0，snapshot 的 events 为原始值10、t1修正值13两行，
tasks 中 r1 为 closed、attempt 为 t1，receipt 等于修正行保存的回执。
同一修正再运行，成果、任务和回执不变。把 t1 改为 t2、value 改为14，追加第三行并以 t2 结案。
此后重投 t1/value13 返回 t1 的旧回执，snapshot 仍以 t2 结案。
CLI 成功 stdout 为 JSON、退出0；业务拒绝 stdout 为 error/message 对象、退出2。
Python 入口的业务拒绝为 ValueError；ResponseLost 是特定的已提交后响应丢失注入。

两侧原断言在 tests/：python3 -m unittest discover -s tests -v。
python3 checks.py normal 运行当前分支原回归；hotfix 分支不包含回放业务测试。
python3 checks.py incident 实际执行提交后丢响应再重试，当前回放分支以
QUARANTINE_REPLAY_DIVERGENCE 断言失败；合并后该命令须通过并打印真实两库行集。
python3 checks.py crash --boundary warehouse_committed 启动 runner 子进程，
等待 hook 后 kill，重开同一命令并核账；另支持 staged、before_close、after_close。
hook 在对应持久操作完成后触发，合并须保留四个命名交接点与其业务含义，
--pause-at 打印 {"hook":名称} 后阻塞标准输入，父进程因此可以确定性终止。
合并后的正常重复请求可直接返回；首次请求必须经过实际交接点，不能跳过注入。
python3 checks.py demo 展示首次正常修正的真实 events/tasks。
所有实验均使用新建临时两库，不依赖账号、网络或预先存在的数据库。

## 维护交付
在 quarantine-replay 上合并 ingest-idempotency，交付一个合并提交；
它的两个父提交须分别为 baseline/replay 与 baseline/hotfix，保留两个分支的原断言，
不得改写标签、删除原测试、改变故障标记或删掉异常注入规避验证。
合并提交包含实现、必要新增核账和维护文档，最终工作区干净。
REVIEW.md 须记录准确的源码路径及行号、事故触发顺序、独立期望与实际、
冲突处理、发布结论及所选持久交接设计；同时比较另一种同契约下可行的设计，
用“t1已入仓但丢响应，以及结案t2后重投t1”的状态说明两种设计分别依赖什么证据，
说明原始回执读取与两库本地事务的兼容边界。
修订 docs/maintenance.md，准确区分原分支现状和合并后行为，写明原命令重试与证据核查方式。
review_evidence.py 提供 verify、demo 两个参数入口。verify 每次实际调用合并后的原业务入口，
重跑两侧原回归、身份冻结及历史重投核账、响应丢失和四个真实 kill/reopen 边界，
以独立读取两个 SQLite 库的完整行关系核对结果，生成 evidence.json 并核对 REVIEW.md 所引案例。
不得仅依赖成功返回、行数或金额合计；独立核账不能调用生产去重或结案判定作为期望。
evidence.json 为 JSON 对象，cases 是案例对象数组，每案至少含 name、输入请求、
expected、actual 和 assertion；字段可自定，expected/actual 必须包含完整成果与任务关系。
demo 展示正常修正、历史重投或中断恢复的真实两库结果与回执。
更新根目录 .pointwise-runtime.json 的 verify/demo，接通 repo/review_evidence.py 对应入口；
保留 version=1、kind=cli、setup 的参数数组列表，verify/demo 均为参数数组，不用 shell 包装。
