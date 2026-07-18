"""Official-first AI and technology source configuration.

Source tiers:
- official: first-party company/lab announcements
- research: primary research sources
- media: reputable independent technology publications
- community: discovery signals only, never treated as confirmation
"""

OFFICIAL_RSS_SOURCES = [
    {
        "name": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
        "home": "https://openai.com/news/",
        "category": "AI Models & Products",
        "base_score": 64,
    },
    {
        "name": "Hugging Face",
        "url": "https://huggingface.co/blog/feed.xml",
        "home": "https://huggingface.co/blog",
        "category": "Open Source AI",
        "base_score": 60,
    },
    {
        "name": "Google AI",
        "url": "https://blog.google/technology/ai/rss/",
        "home": "https://blog.google/technology/ai/",
        "category": "AI Models & Products",
        "base_score": 61,
    },
    {
        "name": "NVIDIA AI",
        "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
        "home": "https://blogs.nvidia.com/",
        "category": "AI Hardware & Infrastructure",
        "base_score": 60,
    },
    {
        "name": "Microsoft Research",
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "home": "https://www.microsoft.com/en-us/research/",
        "category": "AI Research",
        "base_score": 59,
    },
    {
        "name": "AWS Machine Learning",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "home": "https://aws.amazon.com/blogs/machine-learning/",
        "category": "AI Platforms & Developer Tools",
        "base_score": 56,
    },
    {
        "name": "Apple Machine Learning Research",
        "url": "https://machinelearning.apple.com/rss.xml",
        "home": "https://machinelearning.apple.com/",
        "category": "AI Research",
        "base_score": 59,
    },
    {
        "name": "GitHub",
        "url": "https://github.blog/feed/",
        "home": "https://github.blog/",
        "category": "Developer Tools & Open Source",
        "base_score": 55,
    },
    {
        "name": "Cloudflare",
        "url": "https://blog.cloudflare.com/rss/",
        "home": "https://blog.cloudflare.com/",
        "category": "Cloud & Infrastructure",
        "base_score": 54,
    },
]

# Official sites without a dependable public RSS feed are discovered through
# Google News RSS constrained to the official domain. Results remain labelled
# first-party and are rejected when the publisher domain does not match.
OFFICIAL_SITE_QUERIES = [
    {
        "name": "Anthropic",
        "domain": "anthropic.com",
        "home": "https://www.anthropic.com/news",
        "query": 'site:anthropic.com/news (introducing OR model OR research OR product OR safety OR engineering)',
        "category": "AI Models & Products",
        "base_score": 65,
    },
    {
        "name": "Google DeepMind",
        "domain": "deepmind.google",
        "home": "https://deepmind.google/blog/",
        "query": 'site:deepmind.google/blog (introducing OR model OR research OR breakthrough OR release)',
        "category": "AI Research",
        "base_score": 65,
    },
    {
        "name": "Meta AI",
        "domain": "ai.meta.com",
        "home": "https://ai.meta.com/blog/",
        "query": 'site:ai.meta.com/blog (introducing OR model OR research OR open source OR release)',
        "category": "AI Models & Products",
        "base_score": 64,
    },
    {
        "name": "Mistral AI",
        "domain": "mistral.ai",
        "home": "https://mistral.ai/news/",
        "query": 'site:mistral.ai/news (introducing OR model OR research OR product OR release)',
        "category": "AI Models & Products",
        "base_score": 63,
    },
    {
        "name": "Cohere",
        "domain": "cohere.com",
        "home": "https://cohere.com/blog",
        "query": 'site:cohere.com/blog ("product launch" OR introducing OR model OR research OR open-source)',
        "category": "AI Models & Products",
        "base_score": 62,
    },
    {
        "name": "xAI",
        "domain": "x.ai",
        "home": "https://x.ai/news",
        "query": 'site:x.ai/news (Grok OR model OR research OR release OR API)',
        "category": "AI Models & Products",
        "base_score": 62,
    },
    {
        "name": "Stability AI",
        "domain": "stability.ai",
        "home": "https://stability.ai/news-updates",
        "query": 'site:stability.ai/news-updates (introducing OR model OR open-weight OR release OR research)',
        "category": "Generative Media",
        "base_score": 61,
    },
    {
        "name": "Runway",
        "domain": "runwayml.com",
        "home": "https://runwayml.com/news",
        "query": 'site:runwayml.com/news (introducing OR model OR research OR engineering OR release)',
        "category": "Generative Media",
        "base_score": 60,
    },
    {
        "name": "Perplexity",
        "domain": "perplexity.ai",
        "home": "https://www.perplexity.ai/hub/blog",
        "query": 'site:perplexity.ai/hub/blog (introducing OR product OR model OR research OR API)',
        "category": "AI Models & Products",
        "base_score": 59,
    },
    {
        "name": "ElevenLabs",
        "domain": "elevenlabs.io",
        "home": "https://elevenlabs.io/blog",
        "query": 'site:elevenlabs.io/blog (introducing OR model OR research OR product OR release)',
        "category": "Voice & Audio AI",
        "base_score": 60,
    },
    {
        "name": "Groq",
        "domain": "groq.com",
        "home": "https://groq.com/blog",
        "query": 'site:groq.com/blog (introducing OR inference OR model OR API OR LPU OR release)',
        "category": "AI Hardware & Infrastructure",
        "base_score": 59,
    },
    {
        "name": "Cerebras",
        "domain": "cerebras.ai",
        "home": "https://www.cerebras.ai/blog",
        "query": 'site:cerebras.ai/blog (introducing OR inference OR model OR research OR release)',
        "category": "AI Hardware & Infrastructure",
        "base_score": 59,
    },
    {
        "name": "Together AI",
        "domain": "together.ai",
        "home": "https://www.together.ai/blog",
        "query": 'site:together.ai/blog (introducing OR open-source OR inference OR research OR model)',
        "category": "AI Platforms & Developer Tools",
        "base_score": 58,
    },
    {
        "name": "Databricks",
        "domain": "databricks.com",
        "home": "https://www.databricks.com/blog",
        "query": 'site:databricks.com/blog (Mosaic AI OR model OR agent OR machine learning OR release)',
        "category": "AI Platforms & Developer Tools",
        "base_score": 57,
    },
    {
        "name": "IBM Research",
        "domain": "research.ibm.com",
        "home": "https://research.ibm.com/blog",
        "query": 'site:research.ibm.com/blog (AI OR foundation model OR machine learning OR quantum)',
        "category": "AI Research",
        "base_score": 58,
    },
    {
        "name": "Salesforce AI Research",
        "domain": "salesforce.com",
        "home": "https://www.salesforce.com/blog/ai-research/",
        "query": 'site:salesforce.com/blog ("AI Research" OR model OR agent OR benchmark)',
        "category": "AI Research",
        "base_score": 57,
    },
    {
        "name": "Qwen",
        "domain": "qwen.ai",
        "home": "https://qwen.ai/",
        "query": 'site:qwen.ai (introducing OR model OR open source OR release OR research)',
        "category": "Open Source AI",
        "base_score": 62,
    },

    {
        "name": "DeepSeek",
        "domain": "api-docs.deepseek.com",
        "home": "https://api-docs.deepseek.com/news/",
        "query": 'site:api-docs.deepseek.com/news (release OR model OR API OR open-source OR update)',
        "category": "Open Source AI",
        "base_score": 64,
    },
    {
        "name": "AI21 Labs",
        "domain": "ai21.com",
        "home": "https://www.ai21.com/blog/",
        "query": 'site:ai21.com/blog (introducing OR model OR Jamba OR release OR research OR API)',
        "category": "AI Models & Products",
        "base_score": 60,
    },
    {
        "name": "Sakana AI",
        "domain": "sakana.ai",
        "home": "https://sakana.ai/blog/",
        "query": 'site:sakana.ai (research OR model OR release OR evolutionary OR agent)',
        "category": "AI Research",
        "base_score": 61,
    },
    {
        "name": "Adobe AI & Firefly",
        "domain": "blog.adobe.com",
        "home": "https://blog.adobe.com/en/topics/artificial-intelligence",
        "query": 'site:blog.adobe.com/en (Firefly OR "artificial intelligence" OR "generative AI" OR agentic)',
        "category": "Generative Media",
        "base_score": 59,
    },

    {
        "name": "Qwen Technical Blog",
        "domain": "qwenlm.github.io",
        "home": "https://qwenlm.github.io/blog/",
        "query": 'site:qwenlm.github.io/blog (Qwen OR model OR release OR research)',
        "category": "Open Source AI",
        "base_score": 61,
    },
]

RESEARCH_SOURCES = [
    {
        "name": "arXiv AI & Machine Learning",
        "query": "(cat:cs.AI OR cat:cs.LG)",
        "category": "AI Research",
        "base_score": 45,
    },
    {
        "name": "arXiv NLP & Language Models",
        "query": "cat:cs.CL",
        "category": "AI Research",
        "base_score": 45,
    },
    {
        "name": "arXiv Computer Vision",
        "query": "cat:cs.CV",
        "category": "AI Research",
        "base_score": 44,
    },
    {
        "name": "arXiv Robotics",
        "query": "cat:cs.RO",
        "category": "Robotics",
        "base_score": 44,
    },
]

TRUSTED_MEDIA_RSS_SOURCES = [
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "home": "https://www.technologyreview.com/",
        "category": "Independent Technology News",
        "base_score": 34,
    },
    {
        "name": "IEEE Spectrum",
        "url": "https://spectrum.ieee.org/feeds/feed.rss",
        "home": "https://spectrum.ieee.org/",
        "category": "Independent Technology News",
        "base_score": 35,
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "home": "https://arstechnica.com/",
        "category": "Independent Technology News",
        "base_score": 32,
    },
    {
        "name": "Google Security Blog",
        "url": "https://security.googleblog.com/feeds/posts/default",
        "home": "https://security.googleblog.com/",
        "category": "Cybersecurity",
        "base_score": 40,
    },
    {
        "name": "Krebs on Security",
        "url": "https://krebsonsecurity.com/feed/",
        "home": "https://krebsonsecurity.com/",
        "category": "Cybersecurity",
        "base_score": 38,
    },
]
