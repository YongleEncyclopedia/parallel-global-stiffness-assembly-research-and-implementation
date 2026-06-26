# 月度汇报四象限图 figure contract

## 核心结论

- 符号组装 + 数值组装优于无符号直接组装。
- 并行符号组装 + 数值组装优于串行符号组装 + 数值组装。

## 证据链

- 串行有符号相对串行无符号：1.68x。
- 并行有符号相对串行有符号：4.67x。
- 同为 14 线程，并行有符号相对并行无符号：2.52x。

## 边界

- 主图使用同一 WindHub / Apple M4 Max 结果，不用于宣称 Intel 或 Windows 的绝对时间。
- 内存图显示可解释数据结构字节数，不是操作系统 RSS。
- direct/no-symbolic 路径是 `(row,col,value)` contribution list 排序归并，不是 dense matrix。
