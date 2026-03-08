# Mnemo

Mnemo 是统一记忆注入与消费状态的可二开基础工程。

## 架构图

```text
sources(urgent/preconscious/snapshot)
            |
         scanner
            |
       block_builder
            |
       hash_debounce
            |
      unified_injector
            |
   MEMORY.md + consume_state
```

## 快速安装

```bash
cd mnemo
pip install -e .
```

## 快速上手

```bash
python cli/main.py inject --dry-run
python cli/main.py status
python cli/main.py scan --dry-run
```

## 配置说明

- 默认配置：`config/mnemo.default.json`
- 环境变量覆盖：`MNEMO_*`（如 `MNEMO_INJECT__MODE=readonly`）
- 关键字段：
  - `inject.mode`: `readonly|dualwrite|primary`
  - `priority`: 注入优先级数组
  - `feature_flags`: 兼容旧开关

## 开发指南（二开）

- 适配层在 `mnemo/adapters/`：可接 Mem0、Ktao 或自定义后端。
- 注入主流程在 `mnemo/injector/unified_inject.py`。
- 状态迁移在 `mnemo/consumer/consume_state.py` 的 `migrate_from_legacy()`。
- 推荐先扩展 `models.py` 与 `config.py`，再扩展 scanner/ranker。

## 贡献者

- roy chen
- 小武
- 书呆子
