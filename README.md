# Mnemo 🧠

> AI Agent 的记忆管家——让你的 Agent 每次启动都记得"自己是谁、昨天发生了什么"。

---

## 这是什么？

你有没有遇到过这种情况：

- 切换一个模型，Agent 突然"降智"，之前说好的事全忘了
- 上下文压缩（compaction）之后，Agent 开始乱说话
- 每次新会话都要重新介绍一遍背景，烦透了

**Mnemo 就是来解决这个问题的。**

它把三路记忆来源——**紧急信息**（urgent）、**预意识缓冲**（preconscious buffer）、**长期快照**（snapshot）——统一管理，按优先级自动注入到 Agent 的上下文里。不重不漏，hash 防重复，还能灰度切换。

这是我们（roy chen + 小武 + 书呆子）在自己的 AI Agent 系统里跑了一段时间之后，从实战里提炼出来的。

---

## 架构（一张图说明白）

```
┌─────────────────────────────────────────────────┐
│                  三路记忆来源                      │
│                                                   │
│  🚨 urgent-lane/     📥 preconscious/    📚 snapshot  │
│     queue.jsonl          buffer.jsonl      .md    │
└───────────────────┬─────────────────────────────┘
                    │  优先级：urgent > preconscious > snapshot
                    ▼
         ┌─────────────────────┐
         │   unified_inject    │  ← hash 防抖，不重复注入
         │   （统一注入器）      │  ← 消费状态回写
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │      MEMORY.md      │
         │  <!-- MNEMO_START -->│  ← Agent 启动时自动读到这里
         │  <!-- MNEMO_END --> │
         └─────────────────────┘
```

---

## 快速上手

**安装：**
```bash
git clone https://github.com/llw2011/mnemo.git
cd mnemo
pip install -e .
```

**三条命令跑起来：**
```bash
# 看看现在记忆库里有什么
python3 cli/main.py status --workspace /path/to/your/workspace

# 先试跑，不真正写入（放心玩）
python3 cli/main.py inject --workspace /path/to/your/workspace --dry-run

# 确认没问题，正式注入
python3 cli/main.py inject --workspace /path/to/your/workspace --mode primary
```

---

## 灰度切换

不确定要不要全切过来？三档模式任你选：

| 模式 | 行为 |
|------|------|
| `readonly` | 只输出 diff，什么都不写，就是看看 |
| `dualwrite` | 新旧系统同时跑，平滑过渡 |
| `primary` | 全量切换，正式上线 |

---

## 从旧版本迁移

如果你之前用的是分散的三个状态文件（`preconscious_consumed.json` / `preconscious_inject_hash.json` / `snapshot_inject_hash.json`），一条命令搞定迁移：

```bash
python3 tools/migrate_from_v1.py --workspace /path/to/your/workspace
```

会自动备份旧文件，生成迁移报告，不会丢数据。

---

## 二开指南

想接自己的记忆系统？看这几个文件：

- `mnemo/adapters/mem0_adapter.py` — 接 Mem0
- `mnemo/adapters/ktao_adapter.py` — 接 Ktao（或任意 CLI 型记忆工具）
- `config/mnemo.default.json` — 所有开关都在这里
- 环境变量覆盖：`MNEMO_INJECT__MODE=readonly`（双下划线表示层级）

---

## 贡献者

- **roy chen** — 产品方向 & 架构决策
- **小武** — 系统设计 & 集成
- **书呆子**（GPT-5.3 Codex）— 代码实现

---

*"让 Agent 有记忆，不是为了让它记住命令，而是为了让它记住你。"*
