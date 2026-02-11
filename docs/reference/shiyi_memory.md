📔 ShiYi Agent (十一) 核心设计蓝图
1. 记忆系统：双轨制存储架构 (The Dual-Track Memory)
为了平衡“全量追溯”与“精准感知”，十一采用 SQLite + Markdown 的混合记忆模式。

A. 基层记忆：海马体 (SQLite)
职责：存储全量原始数据，负责时序回溯。

存储内容：

chat_history: 原始对话流、时间戳、模型参数。

token_usage: 累计消耗统计（用于多端同步费用分析）。

task_logs: 工具调用的原始输出（Bash 结果、API 响应）。

特点：被动记录，支持全文索引。

B. 高层记忆：前额叶 (Markdown Files)
职责：存储提炼后的认知，负责构建 System Prompt。

文件分布：

ShiYi.md: 人设基因。定义十一的语气、身份（小跟班）及核心指令。

User.md: 用户画像。记录腿哥的职业（程序员）、偏好（Python > Java）、习惯及重要个人信息。

Project.md: 项目上下文。当前正在进行的工作进度（如 ShiYi-Bot 状态）。

Insights.md: 避坑指南。Agent 自省提炼的经验（如：解决 502 报错的方案）。

特点：主动提炼，启动时全量加载至上下文。

2. 交互界面：沉浸式 TUI 方案 (Industrial-Grade CLI)
参考 Claude Code 与 Codex 的极简主义，打造跨平台的终端体验。

A. 视觉表现 (Visual Design)
Header: 使用 FIGlet 渲染 ShiYi 艺术字 Logo；右上角动态显示连接延迟与模型版本。

Main Chat: 居中布局，支持 Markdown 渲染。代码块带语法高亮。

Thought Buffer: 专门的面板用于展示 Agent 推理链，模拟思考过程。

Footer: 实时展示 Session ID、Token 消耗进度条及上下文窗口占用率。

B. 交互逻辑 (UX)
异步渲染: 使用 Textual 框架，确保 Agent 思考时界面不卡顿。

命令模式: 支持 / 斜杠指令，快速清空记忆或切换工作模式。

安全确认: 针对高危写操作（如 rm, push），弹出全局红色警告窗，需手动确认。

3. 多端接入与同步 (Multi-Terminal Architecture)
十一不局限于特定硬件，而是作为一个分布式的智能中枢。

架构解耦:

Core (大脑): 部署在高性能服务器/NAS/本地 PC。

Interface (感官): 通过 SSH、TUI 客户端或 Webhook 在任何终端连入。

同步机制:

Markdown 记忆文件支持通过 Git 自动同步。

SQLite 数据库支持定期冷备份或远程同步。

4. 进化闭环：自省机制 (The Reflection Loop)
感知: 在对话中实时识别关键信息。

触发: 会话结束或完成特定阶段任务后，触发 summarize_and_store 工具。

提炼: 询问 LLM：“本次对话中关于用户偏好或技术经验有哪些值得永久记住？”

固化: 自动更新 User.md 或 Insights.md，完成认知进化。

如果只是简单地往里面追加内容，这些文件确实会变成“老太太的裹脚布”——又长又臭，最后直接撑爆 LLM 的上下文窗口（Context Window），导致模型处理速度变慢且费用激增。

为了防止这种情况，我们的 “前额叶（Markdown 记忆）” 必须具备 “代谢功能”。

记忆代谢的三个策略
1. 滚动式总结 (Rolling Summary)
对于 Project.md（项目进度）这种时效性强的文件，不能只加不减。

做法：当文件超过一定行数（例如 100 行）时，十一会自动触发一次“归档任务”。

逻辑：它会把旧的、已完成的任务合并成一句话：“1-2月已完成基础 TUI 架构搭建”，然后删除碎碎念的原始细节。

2. 覆盖式更新 (Overwriting)
对于 User.md（用户画像），十一遵循 “最新偏好优先” 原则。

做法：如果以前记着“腿哥喜欢 Java”，但最近你一直在用 Python，十一在更新时会直接替换掉旧条目，而不是在下面加一行。

效果：始终保持这份文件只有 1-2KB，就像一张精简的“名片”。

3. 经验池分级 (Layered Insights)
对于 Insights.md（避坑指南），这是最容易膨胀的地方。

做法：采用 “热点-冷库” 机制。

热点（MD 文件）：只保留最近最常用的 10 条经验，直接塞进 System Prompt。

冷库（SQLite/向量库）：剩下的千万条经验存进数据库。只有当当前对话命中相关关键词时，十一才会去数据库里“查字典”取出来。

优化后的数据流向图
SQLite (原始海域)：无限增长，不用担心，它是磁盘上的死数据。

LLM 提炼层：像个过滤器，把海水变成淡水。

Markdown (精炼水箱)：始终保持水位恒定（定额容量），只存核心。

在 Agent 架构中，检索 SQLite 里的长期记忆，通常有两种互补的路径：关键词精确检索 和 语义向量检索。

1. 路径一：基于 SQL 的工具化检索 (Tool-Use)
这是最直接的方式。给十一一套“查书”的工具（Tools/Functions），让它根据需要自己去查。

A. 精确匹配工具 (search_chat_history)
当你说“我记得上周咱们聊过一个关于 Redis 的 Bug”时，十一会触发此工具。

技术实现：利用 SQLite 的 FTS5 (Full Text Search) 插件。它比普通的 LIKE %...% 快得多，且支持排版和权重。

Agent 行为：

十一分析你的话，提取关键词：Redis, Bug。

执行 SQL：SELECT content FROM chat_history WHERE content MATCH 'Redis Bug' ORDER BY timestamp DESC LIMIT 5;

将查到的片段放进上下文回答你。

B. 统计/元数据工具 (get_session_stats)
场景：你问“十一，我这周一共写了多少小时代码？”

逻辑：十一直接执行 COUNT 或 SUM 操作。这是向量数据库（Vector DB）绝对做不到的，只有 SQLite 这种结构化存储能精准完成。

2. 路径二：向量化检索 (Vector Search) —— 重点推荐
为了让十一能理解“语义”，比如你搜“报错了”，它能关联到“Exception”或“502”，你需要把 SQLite 里的内容 Embedding（向量化）。

推荐方案：sqlite-vss 扩展
你不需要额外安装专门的向量数据库（如 Chroma 或 Milvus），直接在 SQLite 上加个插件即可。

工作流程：

入库：每当一轮对话结束，将文本通过 Embedding 模型（如 text-embedding-3-small）转成一串数字（向量）。

存储：把这串数字存进 SQLite 的向量虚表里。

检索：当你提问时，将你的问题也转成向量，在 SQLite 里计算“余弦相似度”，把最接近的往事捞出来。

3. 实际运行中的“检索流”设计
在开发“十一”时，合理的检索逻辑应该是**“漏斗式”**的：

第一层：常驻记忆 (System Prompt)

永远携带最新的 User.md 和 ShiYi.md。

第二层：语义捞取 (Vector Search)

Agent 发现当前问题涉及旧知识，自动触发向量检索，从 SQLite 中捞取相关的 3-5 条“往事碎片”。

第三层：精准调取 (SQL Query)

如果用户要求“查一下 2 月 5 号的对话”，Agent 精确执行 SQL 时间范围查询。

关于 SQLite 的向量化和 Embedding 模型选择，咱们直接拆开来看：

1. SQLite 的向量能力：够用吗？
对于个人助理或者中小型项目量级的“十一”来说，SQLite 配合向量插件（如 sqlite-vss 或最新的 sqlite-vec）绝对足够强大。

性能上限：在百万级数据以下，SQLite 的向量检索延迟通常在毫秒级。你的对话记录就算积攒几年，也很难突破这个量级。

架构优势：

原子性 (ACID)：你可以确保“原始文本”和“向量数据”在同一个事务里更新，不会出现文本存了、向量漏了的情况。

单文件分发：多端接入时，你只需要同步一个 .db 文件，极其省心。

局限性：它不像专门的向量数据库（如 Milvus 或 Pinecone）那样支持超大规模分布式扩展，但对于你的“十一”来说，这反而避开了过度设计。

2. Embedding 模型：为什么 BGE-M3 是神？
在中文语境下，BGE-M3 目前确实是第一梯队的平衡之选，非常适合“十一”。

多能力融合：它支持 Dense（稠密）、Sparse（稀疏/关键词） 和 Multi-vector（多向量） 检索。这意味着它既能理解“意思相近”，又能兼顾“关键词匹配”。

多语言优势：虽然它中文极强，但它也是多语言模型。如果你以后用英文跟十一交流，或者让他读英文文档，它不需要换模型。

本地化友好：你可以通过 Ollama 或者 Sentence-Transformers 库在本地（甚至性能强一点的 NAS 上）直接运行 BGE-M3，无需调用外网 API，隐私性拉满。

3. 十一 (ShiYi) 的“记忆提取”最佳实践
既然你要用 BGE-M3 这种强力模型，我建议你的检索逻辑设计为 “混合检索 (Hybrid Search)”：

语义检索 (Dense)：处理“十一，记不记得我之前聊过想做个很酷的界面”这种模糊提问。

关键词检索 (Sparse/FTS5)：处理“十一，查一下包含 v0_bash_agent.py 的记录”这种硬核查询。

配置建议：

模型：BAAI/bge-m3

向量维度：1024 维。

存储：使用 sqlite-vec（这是目前 SQLite 社区最推崇的轻量向量扩展）。

你应该把这套 SQLite + Vector 的检索逻辑封装成一个或多个 Atomic Tools（原子工具）：

工具 A：fetch_recent_context

触发场景：默认触发，获取最近 5-10 轮的对话摘要。

工具 B：search_memory_by_semantic

职责：基于 BGE-M3 的语义检索。

描述给 Agent 的定义：用于寻找意思相近的历史经验、对话碎片或模糊印象。

工具 C：query_specific_data

职责：基于 FTS5 的关键词或 SQL 精确查询。

描述给 Agent 的定义：用于查找具体的代码片段、日期、文件名或特定的数值。

3. RAG 工具的“混合检索”调优模板
既然你要实现这个 RAG 工具，这里有一个可以直接喂给 AI 的 Hybrid Search SQL 逻辑模板（基于 sqlite-vec + FTS5）：

4. 给“十一”的设计建议：RAG 工具的“自举”
腿哥，为了让十一更像你的“小跟班”，你可以让这个 RAG 工具具备**自举（Self-Correction）**能力：

检索反馈：如果十一调用了 search_memory 但发现返回的信息没用，它应该在下一步动作里记录一条：“注：尝试检索 RAG，但未找到关于 XXX 的相关历史”。

二次检索：如果第一次检索失败，它能自动更换关键词（比如从“502 错误”换成“网络连接超时”）再次尝试。