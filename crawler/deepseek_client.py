"""
DeepSeek API client for paper analysis.
"""
from typing import Optional, Generator, Tuple
from dataclasses import dataclass

from openai import OpenAI

from config import settings


# ==================== 论文摘要分析模板 ====================
# CSS 样式模板 - 深色主题学术报告风格
HTML_STYLE_TEMPLATE = """
请使用以下CSS样式模板生成HTML报告：

```css
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #c9d1d9;
    --text-secondary: #8b949e;
    --accent-blue: #58a6ff;
    --accent-green: #3fb950;
    --accent-purple: #a371f7;
    --accent-orange: #d29922;
    --accent-red: #f85149;
    --border-color: #30363d;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Noto Sans SC', 'Source Han Sans CN', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.8;
    padding: 40px 20px;
}

.container { max-width: 1000px; margin: 0 auto; }

.header {
    text-align: center;
    margin-bottom: 40px;
    padding: 30px;
    background: linear-gradient(135deg, #1a1f35 0%, #0d1117 100%);
    border-radius: 16px;
    border: 1px solid var(--border-color);
    position: relative;
}

.header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-green));
}

.header h1 {
    font-size: 1.8em;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 15px;
}

.header .subtitle { font-size: 1.1em; color: var(--text-secondary); }

.section {
    margin-bottom: 30px;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 25px;
    border: 1px solid var(--border-color);
}

.section h2 {
    font-size: 1.4em;
    color: var(--accent-blue);
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--border-color);
}

.section h3 { font-size: 1.2em; color: var(--accent-green); margin: 20px 0 12px 0; }
.section h4 { font-size: 1.05em; color: var(--accent-purple); margin: 15px 0 10px 0; }
.section p { margin-bottom: 12px; text-align: justify; }

.highlight-box {
    background: var(--bg-tertiary);
    border-left: 4px solid var(--accent-blue);
    padding: 15px;
    margin: 15px 0;
    border-radius: 0 8px 8px 0;
}

.highlight-box.warning { border-left-color: var(--accent-orange); }
.highlight-box.success { border-left-color: var(--accent-green); }
.highlight-box.purple { border-left-color: var(--accent-purple); }

code {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
    color: var(--accent-orange);
}

ul, ol { margin: 12px 0; padding-left: 25px; }
li { margin-bottom: 8px; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 0.95em;
}

th, td {
    padding: 12px;
    text-align: left;
    border: 1px solid var(--border-color);
}

th {
    background: var(--bg-tertiary);
    color: var(--accent-blue);
    font-weight: 600;
}

tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }

.tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 15px;
    font-size: 0.8em;
    margin: 2px;
}

.tag-blue { background: rgba(88, 166, 255, 0.2); color: var(--accent-blue); }
.tag-green { background: rgba(63, 185, 80, 0.2); color: var(--accent-green); }
.tag-purple { background: rgba(163, 113, 247, 0.2); color: var(--accent-purple); }

.footer {
    text-align: center;
    padding: 20px;
    color: var(--text-secondary);
    border-top: 1px solid var(--border-color);
    margin-top: 30px;
    font-size: 0.9em;
}
```

HTML结构示例：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>论文分析报告</title>
    <style>/* 上述CSS样式 */</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>论文标题</h1>
            <p class="subtitle">AI 深度分析报告</p>
        </header>
        
        <section class="section">
            <h2>📋 分析内容标题</h2>
            <p>分析内容...</p>
            <div class="highlight-box success">
                <p>重点内容...</p>
            </div>
        </section>
        
        <footer class="footer">
            <p>由 DeepSeek AI 生成的分析报告</p>
        </footer>
    </div>
</body>
</html>
```
"""


# ==================== 论文全文深度分析模板 ====================
# 更完善的 CSS 样式模板 - 适合长篇深度分析报告
FULLTEXT_HTML_STYLE_TEMPLATE = """
请使用以下完整的CSS样式模板生成HTML深度分析报告。这是一个专业的学术论文分析报告模板，具有丰富的排版组件。

```css
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #c9d1d9;
    --text-secondary: #8b949e;
    --accent-blue: #58a6ff;
    --accent-green: #3fb950;
    --accent-purple: #a371f7;
    --accent-orange: #d29922;
    --accent-red: #f85149;
    --accent-cyan: #39c5cf;
    --border-color: #30363d;
    --code-bg: #1a1f29;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Noto Sans SC', 'Source Han Sans CN', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.8;
    padding: 40px 20px;
}

.container { max-width: 1200px; margin: 0 auto; }

/* 页头样式 */
.header {
    text-align: center;
    margin-bottom: 50px;
    padding: 40px;
    background: linear-gradient(135deg, #1a1f35 0%, #0d1117 100%);
    border-radius: 16px;
    border: 1px solid var(--border-color);
    position: relative;
    overflow: hidden;
}

.header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-green));
}

.header h1 {
    font-size: 2.2em;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 20px;
    line-height: 1.4;
}

.header .subtitle { font-size: 1.2em; color: var(--text-secondary); margin-bottom: 10px; }
.header .meta { font-size: 0.95em; color: var(--text-secondary); }

/* 目录样式 */
.toc {
    background: var(--bg-tertiary);
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 40px;
    border: 1px solid var(--border-color);
}

.toc h3 { color: var(--accent-purple); margin-bottom: 15px; font-size: 1.2em; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { margin: 10px 0; }
.toc a { color: var(--text-secondary); text-decoration: none; transition: color 0.2s; }
.toc a:hover { color: var(--accent-blue); }

/* 章节样式 */
.section {
    margin-bottom: 40px;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 30px;
    border: 1px solid var(--border-color);
}

.section h2 {
    font-size: 1.6em;
    color: var(--accent-blue);
    margin-bottom: 25px;
    padding-bottom: 15px;
    border-bottom: 2px solid var(--border-color);
    display: flex;
    align-items: center;
    gap: 10px;
}

.section h3 { font-size: 1.3em; color: var(--accent-green); margin: 25px 0 15px 0; }
.section h4 { font-size: 1.1em; color: var(--accent-purple); margin: 20px 0 12px 0; }
.section p { margin-bottom: 15px; text-align: justify; }

/* 高亮框样式 */
.highlight-box {
    background: var(--bg-tertiary);
    border-left: 4px solid var(--accent-blue);
    padding: 20px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
}

.highlight-box.warning { border-left-color: var(--accent-orange); }
.highlight-box.success { border-left-color: var(--accent-green); }
.highlight-box.purple { border-left-color: var(--accent-purple); }
.highlight-box.red { border-left-color: var(--accent-red); }

/* 创新点/重点卡片 */
.innovation-card {
    background: linear-gradient(135deg, rgba(88, 166, 255, 0.08) 0%, rgba(163, 113, 247, 0.08) 100%);
    border: 1px solid var(--accent-blue);
    border-radius: 12px;
    padding: 25px;
    margin: 20px 0;
}

.innovation-card h4 { color: var(--accent-blue); margin-bottom: 15px; font-size: 1.15em; }

/* 对比网格 */
.comparison-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin: 25px 0;
}

.comparison-card {
    background: var(--bg-tertiary);
    border-radius: 10px;
    padding: 20px;
    border: 1px solid var(--border-color);
}

.comparison-card h4 { color: var(--accent-orange); margin-bottom: 12px; font-size: 1.05em; }

/* 流程图样式 */
.flow-diagram {
    background: var(--bg-tertiary);
    border-radius: 12px;
    padding: 25px;
    margin: 25px 0;
    text-align: center;
}

.flow-title { font-size: 1.1em; color: var(--accent-purple); margin-bottom: 20px; }

.flow-steps {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
}

.flow-step {
    background: var(--bg-secondary);
    border: 2px solid var(--accent-blue);
    border-radius: 10px;
    padding: 12px 20px;
    min-width: 120px;
}

.flow-step .step-name { font-weight: 600; color: var(--accent-blue); margin-bottom: 5px; }
.flow-step .step-desc { font-size: 0.85em; color: var(--text-secondary); }
.flow-arrow { color: var(--accent-green); font-size: 1.5em; font-weight: bold; }

/* 代码样式 */
code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Source Code Pro', monospace;
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.9em;
    color: var(--accent-cyan);
}

pre {
    background: var(--code-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 20px;
    overflow-x: auto;
    margin: 20px 0;
    position: relative;
}

pre code {
    background: transparent;
    padding: 0;
    color: var(--text-primary);
    font-size: 0.85rem;
    line-height: 1.6;
}

/* 代码块头部（显示文件名/路径） */
.code-header {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 10px 16px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 20px;
}

.code-header + pre {
    margin-top: 0;
    border-radius: 0 0 8px 8px;
}

/* 语法高亮 */
.highlight-keyword { color: var(--accent-purple); }
.highlight-type { color: var(--accent-cyan); }
.highlight-string { color: var(--accent-green); }
.highlight-comment { color: var(--text-secondary); font-style: italic; }
.highlight-number { color: var(--accent-orange); }
.highlight-function { color: var(--accent-blue); }

/* 表格样式 */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 0.95em;
}

th, td {
    padding: 14px 16px;
    text-align: left;
    border: 1px solid var(--border-color);
}

th {
    background: var(--bg-tertiary);
    color: var(--accent-blue);
    font-weight: 600;
}

tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }
tr:hover { background: rgba(88, 166, 255, 0.05); }

/* 列表样式 */
ul, ol { margin: 15px 0; padding-left: 25px; }
li { margin-bottom: 10px; }

/* 标签样式 */
.tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8em;
    margin: 3px;
}

.tag-blue { background: rgba(88, 166, 255, 0.2); color: var(--accent-blue); }
.tag-green { background: rgba(63, 185, 80, 0.2); color: var(--accent-green); }
.tag-purple { background: rgba(163, 113, 247, 0.2); color: var(--accent-purple); }
.tag-orange { background: rgba(210, 153, 34, 0.2); color: var(--accent-orange); }

/* 页脚样式 */
.footer {
    text-align: center;
    padding: 30px;
    color: var(--text-secondary);
    border-top: 1px solid var(--border-color);
    margin-top: 40px;
    font-size: 0.9em;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .header h1 { font-size: 1.6em; }
    .section { padding: 20px; }
    .flow-steps { flex-direction: column; }
    .flow-arrow { transform: rotate(90deg); }
    .comparison-grid { grid-template-columns: 1fr; }
}
```

HTML结构模板 - 请按以下结构组织深度分析报告：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>论文标题 - 深度分析报告</title>
    <style>/* 上述完整CSS样式 */</style>
</head>
<body>
    <div class="container">
        <!-- 页头 -->
        <header class="header">
            <h1>论文标题</h1>
            <p class="subtitle">AI 深度分析报告 - 全文解析</p>
            <p class="meta">作者信息 | 机构 | 发表时间</p>
        </header>
        
        <!-- 目录（可选，建议包含） -->
        <nav class="toc">
            <h3>📑 目录</h3>
            <ul>
                <li><a href="#section1">一、研究背景与问题定义</a></li>
                <li><a href="#section2">二、核心方法与技术细节</a></li>
                <li><a href="#section3">三、主要创新点</a></li>
                <li><a href="#section4">四、实验验证与性能分析</a></li>
                <li><a href="#section5">五、局限性与未来工作</a></li>
                <li><a href="#section6">六、总结</a></li>
            </ul>
        </nav>
        
        <!-- 章节示例 -->
        <section class="section" id="section1">
            <h2>🔬 一、研究背景与问题定义</h2>
            <p>背景介绍...</p>
            
            <h3>1.1 问题背景</h3>
            <p>详细描述...</p>
            
            <!-- 对比卡片组 -->
            <div class="comparison-grid">
                <div class="comparison-card">
                    <h4>方面一</h4>
                    <p>描述...</p>
                </div>
                <div class="comparison-card">
                    <h4>方面二</h4>
                    <p>描述...</p>
                </div>
            </div>
            
            <!-- 高亮框 -->
            <div class="highlight-box success">
                <p><strong>核心观点</strong>：重要内容...</p>
            </div>
        </section>
        
        <section class="section" id="section2">
            <h2>⚙️ 二、核心方法与技术细节</h2>
            
            <!-- 流程图 -->
            <div class="flow-diagram">
                <div class="flow-title">方法流程</div>
                <div class="flow-steps">
                    <div class="flow-step">
                        <div class="step-name">步骤一</div>
                        <div class="step-desc">描述</div>
                    </div>
                    <span class="flow-arrow">→</span>
                    <div class="flow-step">
                        <div class="step-name">步骤二</div>
                        <div class="step-desc">描述</div>
                    </div>
                </div>
            </div>
            
            <h3>2.1 子方法</h3>
            <p>详细描述...</p>
            
            <!-- 代码示例（带文件名头部） -->
            <div class="code-header">example.py (核心算法实现)</div>
            <pre><code><span class="highlight-keyword">def</span> <span class="highlight-function">algorithm</span>(data):
    <span class="highlight-comment"># 初始化参数</span>
    result = <span class="highlight-number">0</span>
    <span class="highlight-keyword">for</span> item <span class="highlight-keyword">in</span> data:
        result += process(item)
    <span class="highlight-keyword">return</span> result</code></pre>
            
            <!-- 简单代码块（无头部） -->
            <pre><code><span class="highlight-comment">// 简单示例</span>
x = compute(input)
output = transform(x)</code></pre>
        </section>
        
        <section class="section" id="section3">
            <h2>💡 三、主要创新点</h2>
            
            <!-- 创新点卡片 -->
            <div class="innovation-card">
                <h4>创新点1：标题</h4>
                <p>详细描述创新之处...</p>
            </div>
            
            <div class="innovation-card">
                <h4>创新点2：标题</h4>
                <p>详细描述创新之处...</p>
            </div>
        </section>
        
        <section class="section" id="section4">
            <h2>📊 四、实验验证与性能分析</h2>
            
            <!-- 表格 -->
            <table>
                <tr>
                    <th>实验项</th>
                    <th>方法A</th>
                    <th>方法B</th>
                </tr>
                <tr>
                    <td>指标1</td>
                    <td>结果</td>
                    <td>结果</td>
                </tr>
            </table>
            
            <div class="highlight-box">
                <p><strong>实验结论</strong>：总结实验发现...</p>
            </div>
        </section>
        
        <section class="section" id="section5">
            <h2>⚠️ 五、局限性与未来工作</h2>
            <ul>
                <li><strong>局限性1</strong>：描述...</li>
                <li><strong>局限性2</strong>：描述...</li>
            </ul>
            
            <h3>未来研究方向</h3>
            <ol>
                <li>方向一...</li>
                <li>方向二...</li>
            </ol>
        </section>
        
        <section class="section" id="section6">
            <h2>🎯 六、总结</h2>
            <div class="highlight-box success">
                <p>论文核心贡献总结...</p>
            </div>
        </section>
        
        <!-- 页脚 -->
        <footer class="footer">
            <p>由 DeepSeek AI 生成的全文深度分析报告</p>
            <p>生成时间: YYYY年MM月DD日</p>
        </footer>
    </div>
</body>
</html>
```

**重要排版要求**：
1. 使用上述完整的CSS样式
2. 合理使用 comparison-grid、flow-diagram、innovation-card 等组件使报告结构清晰
3. 每个主要章节使用 section.section 包裹
4. 重要内容使用 highlight-box 高亮（可选 success/warning/purple/red 类）
5. **代码格式化要求**：
   - 代码块使用 `<pre><code>...</code></pre>` 包裹
   - 如需显示文件名/路径，在 `<pre>` 前添加 `<div class="code-header">文件名</div>`
   - 使用语法高亮类美化代码：
     - `<span class="highlight-keyword">` - 关键字（if, for, def, class, return 等）
     - `<span class="highlight-type">` - 类型名称
     - `<span class="highlight-string">` - 字符串
     - `<span class="highlight-comment">` - 注释
     - `<span class="highlight-number">` - 数字
     - `<span class="highlight-function">` - 函数名
6. 创新点使用 innovation-card 突出显示
7. 对比内容使用 comparison-grid + comparison-card
8. 流程/步骤使用 flow-diagram
9. 表格数据清晰展示
10. 建议包含目录（toc）方便导航
11. h2 标题前加上合适的 emoji 图标
"""


@dataclass
class AnalysisResult:
    """Result of paper analysis."""
    reasoning_content: str  # 思维链内容
    content: str  # 最终回答
    success: bool
    error: Optional[str] = None


class DeepSeekClient:
    """Client for interacting with DeepSeek API."""
    
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_api_base_url
        self.model = settings.deepseek_model
        self.max_tokens = settings.deepseek_max_tokens
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client for DeepSeek."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("DeepSeek API key is not configured. Please set DEEPSEEK_API_KEY.")
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client
    
    def is_configured(self) -> bool:
        """Check if DeepSeek API is properly configured."""
        return bool(self.api_key)
    
    def analyze_abstract(
        self,
        abstract: str,
        prompt: str,
        title: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze a paper abstract using DeepSeek.
        
        Args:
            abstract: The paper abstract to analyze
            prompt: User-specified analysis prompt/direction
            title: Optional paper title for context
        
        Returns:
            AnalysisResult containing reasoning and final answer
        """
        if not self.is_configured():
            return AnalysisResult(
                reasoning_content="",
                content="",
                success=False,
                error="DeepSeek API key is not configured. Please set DEEPSEEK_API_KEY in your environment."
            )
        
        # Build the message
        system_message = """你是一位资深的学术论文分析专家。
你的任务是根据用户的具体分析要求，对论文摘要进行深入、专业的分析。
请提供清晰、有洞察力、结构良好的分析结果。"""
        
        user_message = f"""请根据指定的分析方向，分析以下论文摘要。

**分析方向/提示词:**
{prompt}

"""
        if title:
            user_message += f"""**论文标题:**
{title}

"""
        user_message += f"""**摘要:**
{abstract}

请根据指定方向提供你的分析。

**重要输出要求:**
1. 请用中文输出你的分析结果
2. 请直接以HTML文件的形式输出你的回答
3. 输出完整的HTML文档（包含<!DOCTYPE html>、<html>、<head>、<body>等标签）
4. 请严格使用以下提供的CSS样式模板，保持深色主题学术报告风格
5. 在header部分显示论文标题和"AI 深度分析报告"副标题
6. 根据分析内容合理组织section结构
7. 适当使用highlight-box来突出重要观点
8. 在footer显示"由 DeepSeek AI 生成的分析报告"和生成时间

{HTML_STYLE_TEMPLATE}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                stream=False
            )
            
            # Extract content
            message = response.choices[0].message
            reasoning_content = getattr(message, 'reasoning_content', '') or ''
            content = message.content or ''
            
            return AnalysisResult(
                reasoning_content=reasoning_content,
                content=content,
                success=True
            )
        
        except Exception as e:
            return AnalysisResult(
                reasoning_content="",
                content="",
                success=False,
                error=str(e)
            )
    
    def analyze_abstract_stream(
        self,
        abstract: str,
        prompt: str,
        title: Optional[str] = None
    ) -> Generator[Tuple[str, str, bool], None, None]:
        """
        Analyze a paper abstract using DeepSeek with streaming.
        
        Args:
            abstract: The paper abstract to analyze
            prompt: User-specified analysis prompt/direction
            title: Optional paper title for context
        
        Yields:
            Tuples of (reasoning_chunk, content_chunk, is_reasoning)
        """
        if not self.is_configured():
            yield ("", "Error: DeepSeek API key is not configured.", False)
            return
        
        system_message = """你是一位资深的学术论文分析专家。
你的任务是根据用户的具体分析要求，对论文摘要进行深入、专业的分析。
请提供清晰、有洞察力、结构良好的分析结果。"""
        
        user_message = f"""请根据指定的分析方向，分析以下论文摘要。

**分析方向/提示词:**
{prompt}

"""
        if title:
            user_message += f"""**论文标题:**
{title}

"""
        user_message += f"""**摘要:**
{abstract}

请根据指定方向提供你的分析。

**重要输出要求:**
1. 请用中文输出你的分析结果
2. 请直接以HTML文件的形式输出你的回答
3. 输出完整的HTML文档（包含<!DOCTYPE html>、<html>、<head>、<body>等标签）
4. 请严格使用以下提供的CSS样式模板，保持深色主题学术报告风格
5. 在header部分显示论文标题和"AI 深度分析报告"副标题
6. 根据分析内容合理组织section结构
7. 适当使用highlight-box来突出重要观点
8. 在footer显示"由 DeepSeek AI 生成的分析报告"和生成时间

{HTML_STYLE_TEMPLATE}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                stream=True
            )
            
            for chunk in response:
                delta = chunk.choices[0].delta
                reasoning_content = getattr(delta, 'reasoning_content', None)
                content = delta.content
                
                if reasoning_content:
                    yield (reasoning_content, "", True)
                elif content:
                    yield ("", content, False)
        
        except Exception as e:
            yield ("", f"Error: {str(e)}", False)
    
    def analyze_fulltext_stream(
        self,
        fulltext: str,
        prompt: str,
        title: Optional[str] = None
    ) -> Generator[Tuple[str, str, bool], None, None]:
        """
        Analyze paper fulltext using DeepSeek with streaming.
        
        Args:
            fulltext: The full text content from PDF
            prompt: User-specified analysis prompt/direction
            title: Optional paper title for context
        
        Yields:
            Tuples of (reasoning_chunk, content_chunk, is_reasoning)
        """
        if not self.is_configured():
            yield ("", "Error: DeepSeek API key is not configured.", False)
            return
        
        system_message = """你是一位资深的学术论文分析专家。
你的任务是根据用户的具体分析要求，对论文的完整内容进行深入、专业的分析。
请提供清晰、有洞察力、结构良好的深度分析报告。"""
        
        user_message = f"""请根据指定的分析方向，对以下论文的完整内容进行深度分析。

**分析方向/提示词:**
{prompt}

"""
        if title:
            user_message += f"""**论文标题:**
{title}

"""
        # Truncate fulltext if too long (leave room for other content and response)
        max_fulltext_length = 60000  # Leave room for prompt, response, etc.
        if len(fulltext) > max_fulltext_length:
            fulltext = fulltext[:max_fulltext_length] + "\n\n[... 文本已截断 ...]"
        
        user_message += f"""**论文全文内容:**
{fulltext}

请根据指定方向提供你的深度分析。

**重要输出要求:**
1. 请用中文输出你的分析结果
2. 请直接以HTML文件的形式输出你的回答
3. 输出完整的HTML文档（包含<!DOCTYPE html>、<html>、<head>、<body>等标签）
4. 请严格使用以下提供的完整CSS样式模板，保持深色主题学术报告风格
5. 在header部分显示论文标题、"AI 深度分析报告 - 全文解析"副标题，以及作者/机构信息
6. 建议包含目录（toc）方便导航
7. 根据论文内容合理组织section结构，建议包括：研究背景与问题定义、核心方法与技术细节、主要创新点、实验验证与性能分析、局限性与未来工作、总结等
8. 充分使用模板中的组件：
   - innovation-card 突出显示创新点
   - comparison-grid + comparison-card 对比不同方法/方案
   - flow-diagram + flow-step 展示流程/步骤
   - highlight-box（可选 success/warning/purple/red）高亮重要内容
   - table 清晰展示数据和对比
9. h2 章节标题前加上合适的 emoji 图标（如 🔬 ⚙️ 💡 📊 ⚠️ 🎯）
10. 在footer显示"由 DeepSeek AI 生成的全文深度分析报告"和生成时间

{FULLTEXT_HTML_STYLE_TEMPLATE}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                stream=True
            )
            
            for chunk in response:
                delta = chunk.choices[0].delta
                reasoning_content = getattr(delta, 'reasoning_content', None)
                content = delta.content
                
                if reasoning_content:
                    yield (reasoning_content, "", True)
                elif content:
                    yield ("", content, False)
        
        except Exception as e:
            yield ("", f"Error: {str(e)}", False)
    
    def batch_analyze(
        self,
        papers: list,
        prompt: str
    ) -> list:
        """
        Analyze multiple paper abstracts.
        
        Args:
            papers: List of dicts with 'title' and 'abstract' keys
            prompt: Analysis prompt to apply to all papers
        
        Returns:
            List of AnalysisResult objects
        """
        results = []
        for paper in papers:
            result = self.analyze_abstract(
                abstract=paper.get('abstract', ''),
                prompt=prompt,
                title=paper.get('title')
            )
            results.append({
                'title': paper.get('title'),
                'paper_id': paper.get('id'),
                'result': result
            })
        return results
