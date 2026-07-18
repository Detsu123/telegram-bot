"""Technology news sources.

A failed feed is skipped, so one unavailable website will not stop the bot.
You can add or remove RSS/Atom URLs in RSS_SOURCES.
"""

RSS_SOURCES = [
    {
        "name": "OpenAI News",
        "url": "https://openai.com/news/rss.xml",
        "base_score": 35,
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "base_score": 30,
    },
    {
        "name": "Google AI",
        "url": "https://blog.google/technology/ai/rss/",
        "base_score": 32,
    },
    {
        "name": "NVIDIA AI",
        "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
        "base_score": 28,
    },
    {
        "name": "Microsoft Research",
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "base_score": 27,
    },
]

ARXIV_QUERIES = [
    {
        "name": "arXiv AI + ML",
        "query": "(cat:cs.AI OR cat:cs.LG)",
        "base_score": 18,
    },
    {
        "name": "arXiv NLP",
        "query": "cat:cs.CL",
        "base_score": 18,
    },
    {
        "name": "arXiv Computer Vision",
        "query": "cat:cs.CV",
        "base_score": 18,
    },
    {
        "name": "arXiv Robotics",
        "query": "cat:cs.RO",
        "base_score": 18,
    },
]
