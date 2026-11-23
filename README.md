# Resume Auto Tailor

一个可分享的 coding-agent skill：根据职位描述定制简历，检查事实来源、项目匹配、文字质量与最终 PDF。支持 Codex 等能够读取 `SKILL.md`、运行 Python/Node 命令和查看图片的 agent。

包内只有通用代码、指南、空白模板和偏好示例。用户的简历、偏好、职位描述及生成结果保存到自己的工作目录。

## 安装与第一次使用

把整个目录作为 `resume-auto-tailor` skill 安装到你的 agent 支持的 skills 目录；也可以直接让 agent 打开本仓库的 `SKILL.md`。保留 scripts、references、assets 等配套文件。

安装时把下面这段交给 coding agent：

> 请安装并使用这个目录中的 resume-auto-tailor skill。先读取 SKILL.md 和 references/onboarding.md，检查我的简历工作目录。若尚未设置，请引导我导入自己的完整简历，说明并设置可选偏好，然后验证模板和设置能正常使用。不要把示例占位符当作我的经历。

安装后支持 `$skill-name` 的宿主可输入：`$resume-auto-tailor 帮我设置简历模板和偏好`。首次运行会先检查设置。**静态 skill 不能保证安装完成便自动弹出对话**；安装 agent 应按上面的指令立即开始引导，其他情况在第一次使用时引导。

你可以使用已有 HTML、Word、PDF 或文本简历，由 agent 转成可检查的 HTML master；或从空白模板开始。可设置：简历语言、Letter/A4、页数目标与上限、栏目顺序、是否有摘要、项目数量与不足时的处理、技能排序、特定经历的保留条件。没有强制两页或三个项目。

## 依赖

- Python 3.11+：`python -m pip install -r requirements.txt`
- Node.js/npm：在 skill 目录运行 `npm ci`，再运行 `npx playwright install chromium`
- Poppler：确保 `pdftoppm` 在 PATH 中，用于 PDF 转图片
- Agent 需要读取职位描述、编辑本地文件和查看生成图片的能力。安装细节交由 agent 按当前平台处理。

初始化：`python scripts/setup_profile.py init --workspace <你的工作目录>`；检查：`python scripts/setup_profile.py status --workspace <你的工作目录>`。这些命令只准备和检查文件；事实核对、偏好选择与最终视觉评审由 agent 配合用户完成。

## 保留的功能

- JD 需求拆解、证据库、可追溯改写和数字/职位事实检查。
- 项目直接相关性检查、首条内容突出匹配点、可选最新项目补位。
- 只读评审及最多两轮修改；明确独立评审是否可用。
- HTML 排版检查、自然分页、PDF 生成、可提取文字与栏目顺序检查。
- 逐页及跨页视觉检查、版本化输出与文件缓存排查。

详细流程在 [SKILL.md](SKILL.md)，首次引导在 [references/onboarding.md](references/onboarding.md)。HTML 结构范围与检查边界见 [references/template-contract.md](references/template-contract.md)。默认不发送或提交简历。

## 分享与测试

只分享通用 skill 文件。`private/` 和 `output/` 已加入忽略规则；不要把填好的简历、偏好、输出、缓存或 node_modules 打包给别人。用户资料最好放在独立的工作目录。

运行 `python -m unittest discover -s tests -v`。测试数据为虚构示例，不包含原用户简历。
