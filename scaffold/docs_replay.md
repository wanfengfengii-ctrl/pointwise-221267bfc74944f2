# 隔离修正运行说明
runner.py replay 接收 record、attempt、payload，先写发送状态，再入仓并结案。
attempt 已作为入仓参数，因此响应丢失后可以直接原请求重试，不会重复入账。
tasks 中保存了最近一次发送内容；state=closed 表明对应修正已经持久入仓。
后续修正仍使用同一 record，只需提供新的 attempt。旧请求重试不会影响新结案。
四个 hook 仅供维护实验；在 hook 处终止进程后原命令重跑即可。
