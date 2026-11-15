# 入仓幂等维护说明
原始记录按 record 去重，重投返回最初持久回执；同号异内容拒绝。
events 内成果与 receipt 一起提交。original_receipt(record) 保留三字段旧回执。
当前分支不支持修正尝试。
