# 文档语言例外清单

本仓库给人阅读的新文档默认使用中文。下面这些 tracked 文本文件服务工具或配置流程，字段、占位符或语法不适合强制翻译；它们不作为人工维护时的项目事实入口。

## 允许保留英文的工具文件

- `.serena/memories/memory_maintenance.md`：Serena 工具记忆规范，供代理工具读取。
- `.spec-workflow/templates/*.md`：spec workflow 模板，占位符和字段结构可能被工具消费，包含 requirements/design/tasks/tech/structure/product 等模板。
- `.spec-workflow/user-templates/README.md`：用户模板目录说明，属于 spec workflow 工具入口。

## 配置文件说明

- `CMakePresets.json` 不支持注释；它为什么放在 CPU 主线根部，由 `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md` 的目录维护说明解释。
- `CMakeLists.txt` 支持 `#` 注释，文件头保留中文说明，但 CMake 命令和 option 名称保持英文。
