# Mnemo

Mnemo 是 Plan B（Ktao + Preconscious 合并，Mem0 独立）的统一注入与状态管理工具。

## 架构图（Plan B 实际数据流）

```text
memory/urgent-lane/queue.jsonl
memory/preconscious/buffer.jsonl
memory/layer1/snapshot.md
              |
              v
   mnemo/injector/unified_inject.py
   - priority: urgent > preconscious > snapshot
   - hash debounce: state/unified_inject_hash.json
   - consume writeback: state/unified_consume_state.json
              |
              v
    MEMORY.md
    <!-- MNEMO_START --> ... <!-- MNEMO_END -->

Legacy(v1): memory/state/*.json
              |
              v
   mnemo/tools/migrate_from_v1.py
   -> state/unified_consume_state.json
```

## 快速安装

```bash
cd /home/node/.openclaw/workspace-tg/mnemo
pip install -e .
```

## 快速上手（可直接运行）

```bash
# 1) 扫描（调用 tools/preconscious_scan.py）
python3 mnemo/cli/main.py scan --workspace /home/node/.openclaw/workspace-tg --dry-run

# 2) 注入（readonly / dualwrite / primary）
python3 mnemo/cli/main.py inject --workspace /home/node/.openclaw/workspace-tg --mode readonly --dry-run
python3 mnemo/cli/main.py inject --workspace /home/node/.openclaw/workspace-tg --mode dualwrite
python3 mnemo/cli/main.py inject --workspace /home/node/.openclaw/workspace-tg --mode primary

# 3) 状态
python3 mnemo/cli/main.py status --workspace /home/node/.openclaw/workspace-tg

# 4) 回滚（调用 tools/preconscious_rollback.sh）
python3 mnemo/cli/main.py rollback --workspace /home/node/.openclaw/workspace-tg
```

## 从 v1 迁移

```bash
python3 mnemo/tools/migrate_from_v1.py --workspace /home/node/.openclaw/workspace-tg
```

迁移动作：
1. 备份旧文件到 `.bak.migrate`：
   - `memory/state/preconscious_consumed.json`
   - `memory/state/preconscious_inject_hash.json`
   - `memory/state/snapshot_inject_hash.json`
2. 调用 `migrate_from_legacy()` 合并为 `state/unified_consume_state.json`
3. 校验必要字段并生成 `state/migration_report.json`

## 配置说明

- 默认配置：`config/mnemo.default.json`
- 环境变量覆盖：`MNEMO_*`（例如 `MNEMO_INJECT__MODE=readonly`）
- 关键字段：
  - `inject.mode`: `readonly|dualwrite|primary`
  - `priority`: 注入优先级数组

## 贡献者

- roy chen
- 小武
- 书呆子
