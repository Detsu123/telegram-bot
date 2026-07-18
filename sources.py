"""Technology Digest V2 source configuration."""

RSS_SOURCES = [
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "category": "AI & Models", "base_score": 42},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "category": "AI & Models", "base_score": 38},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "category": "AI & Models", "base_score": 38},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "category": "AI & Models", "base_score": 40},
    {"name": "NVIDIA AI", "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/", "category": "AI & Models", "base_score": 36},
    {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/", "category": "Research", "base_score": 34},
    {"name": "AWS Machine Learning", "url": "https://aws.amazon.com/blogs/machine-learning/feed/", "category": "AI & Models", "base_score": 31},
    {"name": "Apple Machine Learning", "url": "https://machinelearning.apple.com/rss.xml", "category": "AI & Models", "base_score": 35},

    {"name": "GitHub Blog", "url": "https://github.blog/feed/", "category": "Software & Open Source", "base_score": 31},
    {"name": "GitHub Changelog", "url": "https://github.blog/changelog/feed/", "category": "Software & Open Source", "base_score": 32},
    {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/", "category": "Cloud & Infrastructure", "base_score": 32},
    {"name": "Mozilla Hacks", "url": "https://hacks.mozilla.org/feed/", "category": "Software & Open Source", "base_score": 28},
    {"name": "Chromium Blog", "url": "https://blog.chromium.org/feeds/posts/default", "category": "Software & Open Source", "base_score": 29},
    {"name": "Android Developers", "url": "https://android-developers.googleblog.com/feeds/posts/default", "category": "Consumer Tech", "base_score": 28},
    {"name": "Raspberry Pi", "url": "https://www.raspberrypi.com/news/feed/", "category": "Hardware", "base_score": 27},

    {"name": "Google Security Blog", "url": "https://security.googleblog.com/feeds/posts/default", "category": "Cybersecurity", "base_score": 36},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "category": "Cybersecurity", "base_score": 36},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/", "category": "Cybersecurity", "base_score": 31},

    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "General Technology", "base_score": 31},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "Startups & Business", "base_score": 28},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "Consumer Tech", "base_score": 27},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "category": "Research", "base_score": 34},
    {"name": "IEEE Spectrum", "url": "https://spectrum.ieee.org/feeds/feed.rss", "category": "Research", "base_score": 35},
    {"name": "NASA", "url": "https://www.nasa.gov/feed/", "category": "Space & Science", "base_score": 34},
    {"name": "SpaceNews", "url": "https://spacenews.com/feed/", "category": "Space & Science", "base_score": 30},
]

GOOGLE_NEWS_QUERIES = [
    {"name": "AI model releases", "query": '"new AI model" OR "AI model release" OR "foundation model"', "category": "AI & Models", "base_score": 25},
    {"name": "Technology breakthroughs", "query": '"technology breakthrough" OR "scientific breakthrough" technology', "category": "Research", "base_score": 25},
    {"name": "Open-source releases", "query": '"open source" software release OR developer tool', "category": "Software & Open Source", "base_score": 23},
    {"name": "Cybersecurity", "query": 'cybersecurity vulnerability OR data breach OR security update', "category": "Cybersecurity", "base_score": 25},
    {"name": "Chips and hardware", "query": 'semiconductor OR AI chip OR GPU OR processor launch', "category": "Hardware", "base_score": 24},
    {"name": "Robotics", "query": 'robotics OR humanoid robot OR autonomous robot', "category": "Robotics", "base_score": 24},
    {"name": "Space technology", "query": 'space technology OR rocket launch OR satellite technology', "category": "Space & Science", "base_score": 23},
    {"name": "Consumer technology", "query": 'smartphone launch OR laptop launch OR wearable technology', "category": "Consumer Tech", "base_score": 20},
    {"name": "Technology startups", "query": 'technology startup funding OR startup acquisition', "category": "Startups & Business", "base_score": 20},
]

ARXIV_QUERIES = [
    {"name": "arXiv AI + ML", "query": "(cat:cs.AI OR cat:cs.LG)", "category": "AI & Models", "base_score": 19},
    {"name": "arXiv NLP", "query": "cat:cs.CL", "category": "AI & Models", "base_score": 19},
    {"name": "arXiv Computer Vision", "query": "cat:cs.CV", "category": "Research", "base_score": 19},
    {"name": "arXiv Robotics", "query": "cat:cs.RO", "category": "Robotics", "base_score": 19},
]
