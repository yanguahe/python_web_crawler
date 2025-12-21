"""
DeepSeek API client for paper analysis.
"""
from typing import Optional, Generator, Tuple
from dataclasses import dataclass

from openai import OpenAI

from config import settings


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
4. 请严格使用以下提供的CSS样式模板，保持深色主题学术报告风格
5. 在header部分显示论文标题和"AI 深度分析报告 - 全文解析"副标题
6. 根据论文内容合理组织section结构，包括但不限于：研究背景、主要贡献、方法论、实验结果、结论与展望等
7. 适当使用highlight-box来突出重要观点和创新点
8. 在footer显示"由 DeepSeek AI 生成的全文深度分析报告"和生成时间

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
