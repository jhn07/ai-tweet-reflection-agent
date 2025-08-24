# 📚 HELPER.md - Tweet AI Agent Usage Guide

Complete guide for using the AI tweet generation system from basic launch to advanced management.

## 🚀 QUICK START

### 1. First Launch
```bash
# Make sure you have a .env file with OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env

# Run tweet generation
python main.py
```

**What happens:**
- System generates a tweet on the given topic
- Automatically critiques quality (score 0.0-1.0)
- Rewrites for improvement if needed
- Tracks each step with detailed progress information
- Outputs final result with metrics and step-by-step breakdown

### 2. Changing Tweet Topic
Edit line 68 in `main.py`:
```python
"messages": [HumanMessage(content="Your new tweet topic")]
```

Example topics:
- "Impact of AI on education"
- "Future of electric vehicles"
- "Benefits of remote work"
- "New technologies in medicine"

### 3. Language Switching
In `main.py` change the language parameter:
```python
"language": "en"  # for English
"language": "ru"  # for Russian (default)
```

## 🔧 MODEL MANAGEMENT

### View Status of All Models
```bash
python model_switcher.py status
```

**Example output:**
```
=== CURRENT PROVIDER STATUS ===

GENERATION:
  Provider: openai:gpt-4o-mini
  Available: ✅
  Configuration:
    model_name: gpt-4o-mini
    temperature: 0.4
```

### Model Switching

#### Change Generation Model
```bash
# Switch to more powerful model
python model_switcher.py switch generation gpt-4o --temperature 0.6

# Switch to economical model
python model_switcher.py switch generation gpt-4o-mini --temperature 0.4

# Switch to more creative temperature
python model_switcher.py switch generation gpt-4o --temperature 0.8
```

#### Change Critique Model
```bash
# Stricter critique (temperature 0.0)
python model_switcher.py switch critique gpt-4o --temperature 0.0

# Softer critique
python model_switcher.py switch critique gpt-4o-mini --temperature 0.1
```

#### Change Rewrite Model
```bash
# Higher quality rewriting
python model_switcher.py switch rewrite gpt-4o --temperature 0.5
```

### Performance Testing

#### Test Single Model
```bash
# Test generation model
python model_switcher.py test generation --message "Create a tweet about Python"

# Test critique model
python model_switcher.py test critique --message "Rate this tweet: Python is the best programming language!"
```

#### Compare Models
```bash
# Compare performance of different models
python model_switcher.py compare gpt-4o-mini gpt-4o gpt-3.5-turbo --message "Tweet about AI"

# Compare with custom message
python model_switcher.py compare gpt-4o-mini gpt-4o --message "Environmental technologies in 2024"
```

**Example comparison result:**
```
=== COMPARISON RESULTS ===

🤖 gpt-4o-mini:
   ⏱️  Time: 2.34s
   🔢 Tokens: 45
   💰 Cost: $0.000090
   📝 Response: AI is revolutionizing ecology...

🤖 gpt-4o:
   ⏱️  Time: 3.12s
   🔢 Tokens: 52
   💰 Cost: $0.000156
   📝 Response: Innovative eco-technologies...
```

### Setting Up Fallback Providers
```bash
# Add backup model for generation
python model_switcher.py fallback generation gpt-3.5-turbo

# Add backup model for critique
python model_switcher.py fallback critique gpt-4o-mini

# Add backup model for rewriting
python model_switcher.py fallback rewrite gpt-3.5-turbo
```

**Why fallback providers are needed:**
- Automatic switching when main model fails
- Increases system reliability
- Uninterrupted production operation

## 💾 CACHE MANAGEMENT

### Cache Monitoring

#### View Statistics
```bash
python cache_manager.py stats
```

**Example output:**
```
=== CACHE STATISTICS ===
Size: 45/1000
Hits: 23
Misses: 67
Hit Rate: 25.6%
Evictions: 0
TTL: 3600 seconds
Persistence: ✅
```

#### View Contents
```bash
python cache_manager.py show
```

**Shows:**
- Keys of cached requests
- Models used
- Token count and cost
- Access frequency for entries
- Response previews

### Cache Testing
```bash
python cache_manager.py test
```

**What gets tested:**
- Speed of first request (without cache)
- Speed of repeat request (from cache)
- Speedup from caching
- Updated hit statistics

### Cache Management

#### Cache Clearing
```bash
# Full clear
python cache_manager.py clear

# Remove only expired entries
python cache_manager.py cleanup
```

#### Parameter Configuration
```bash
# Increase cache size to 2000 entries
python cache_manager.py config --max-size 2000

# Set TTL to 2 hours (7200 seconds)
python cache_manager.py config --ttl 7200

# Combined configuration
python cache_manager.py config --max-size 2000 --ttl 7200
```

**Cache configuration recommendations:**
- **Size**: 1000-5000 for production, 100-500 for development
- **TTL**: 1-24 hours depending on prompt change frequency
- **Cleanup**: regularly remove expired entries

## ⚙️ SYSTEM CONFIGURATION

### Environment Variables (.env)

#### Required
```bash
# OpenAI API key (required)
OPENAI_API_KEY=your_key_here
```

#### Optional
```bash
# Default model
MODEL_NAME=gpt-4o-mini

# Temperature (creativity)
TEMPERATURE=0.4

# Quality threshold (0.0-1.0)
QUALITY_SCORE_THRESHOLD=0.78

# Maximum improvement iterations
MAX_ITERS_DEFAULT=3

# Maximum retry attempts on errors
MAX_RETRIES=3

# Request timeout (seconds)
REQUEST_TIMEOUT=120

# Default language
DEFAULT_LANGUAGE=ru
```

### Programmatic Configuration

#### Basic Configuration
```python
from config import TweetAgentConfig

config = TweetAgentConfig(
    model_name="gpt-4o",
    temperature=0.6,
    quality_threshold=0.85,
    max_retries=5
)
```

#### Task-Specific Configurations

**Fast generation (economical):**
```python
fast_config = TweetAgentConfig(
    model_name="gpt-4o-mini",
    temperature=0.7,
    max_iters=1,
    quality_threshold=0.7
)
```

**Quality generation (expensive):**
```python
quality_config = TweetAgentConfig(
    model_name="gpt-4o",
    temperature=0.4,
    max_iters=5,
    quality_threshold=0.9
)
```

**Creative generation:**
```python
creative_config = TweetAgentConfig(
    model_name="gpt-4o",
    temperature=0.8,
    max_iters=3,
    quality_threshold=0.75
)
```

## 📊 PROGRESS TRACKING

### NEW: Step-by-Step Workflow Monitoring

The system now provides detailed tracking of each workflow step with comprehensive information.

#### Understanding Step Information

Each step in the workflow contains:
```python
{
    "type": "generation|critique|rewrite",
    "title": "Human-readable step name", 
    "content": "Brief content preview",
    "score": 0.85,  # Quality score (for critique steps)
    "issues": ["List of identified problems"],
    "tips": ["List of improvement suggestions"]  
}
```

#### Accessing Progress Information

```python
result = graph.invoke(state)

# View planned workflow stages
print("PLANNED STEPS:", result.get("planned_steps"))
# Output: ['Generation', 'Critique', 'Rewrite', 'Final Review']

# View executed steps with details
for i, step in enumerate(result.get("steps", []), 1):
    print(f"{i}. {step['title']} ({step['type']})")
    if step.get('score'):
        print(f"   Score: {step['score']:.2f}")
    if step.get('issues'):
        print(f"   Issues: {', '.join(step['issues'])}")
```

#### Step Types

**Generation Steps:**
- Type: `generation`
- Contains: Tweet content preview
- Score: Not applicable

**Critique Steps:**
- Type: `critique` 
- Contains: Quality assessment details
- Score: 0.0-1.0 quality rating
- Issues: List of identified problems
- Tips: Improvement suggestions

**Rewrite Steps:**
- Type: `rewrite`
- Contains: Improved content preview  
- Tips: Issues being addressed

#### Real-World Example

```
PLANNED STEPS: ['Generation', 'Critique', 'Rewrite', 'Final Review']
EXECUTED STEPS:
  1. Tweet Generation (generation)
     Content: AI transforms healthcare by enhancing diagnostic precision...
  2. Quality Assessment (critique)
     Content: Score: 0.75
     Score: 0.75
     Issues: Tweet could be more engaging, Add specific examples
     Tips: Include real-world applications, Use more dynamic language
  3. Tweet Improvement (rewrite)  
     Content: Improved version: AI revolutionizes healthcare with 95% diagnostic...
     Tips: Tweet could be more engaging, Add specific examples
  4. Quality Assessment (critique)
     Content: Score: 0.92
     Score: 0.92
```

## 📊 MONITORING AND DEBUGGING

### Understanding Logs

#### Log Structure
```
2025-08-20 13:50:20,995 - agents.monitoring - INFO - [7041e941] - Started request
2025-08-20 13:50:23,833 - agents.monitoring - INFO - [7041e941] - Completed request
```

**Breakdown:**
- `2025-08-20 13:50:20,995` - Timestamp
- `agents.monitoring` - Source module
- `INFO` - Log level
- `[7041e941]` - Correlation ID for tracking
- `Started/Completed request` - Event

#### Correlation IDs
- Each request gets a unique ID
- Allows tracking the entire request path
- Useful for debugging production issues

### Performance Metrics

#### After Each Run
System automatically outputs:
```
============================================================
[generation] iter=0 needs=True score=None
============================================================
```

**Breakdown:**
- `generation` - Current node
- `iter=0` - Iteration number
- `needs=True` - Whether refinement is needed
- `score=None/0.85` - Quality score

#### Final Metrics
```
========== FINAL ==========
Tweet...
============================================================
reason: accepted | best_score: 0.90
candidates: [('Tweet1', 0.75), ('Tweet2', 0.90)]
PLANNED STEPS: ['Generation', 'Critique', 'Rewrite', 'Final Review']
EXECUTED STEPS:
  1. Tweet Generation (generation)
     Content: AI revolutionizes healthcare by improving diagnostic accuracy...
  2. Quality Assessment (critique) 
     Content: Score: 0.90
     Score: 0.90
```

### Problem Diagnosis

#### Check Model Availability
```bash
python model_switcher.py status
```

#### Check Cache
```bash
# Statistics
python cache_manager.py stats

# Contents
python cache_manager.py show
```

#### Test Individual Components
```bash
# Test generation model
python model_switcher.py test generation --message "test"

# Test caching
python cache_manager.py test
```

## 🔄 ADVANCED USAGE

### Batch Processing

#### Process List of Topics
```python
from main import graph
from config import DEFAULT_INITIAL_STATE
from langchain_core.messages import HumanMessage

topics = [
    "AI in medicine",
    "Future of transportation",
    "Environmental technologies",
    "Blockchain and finance",
    "VR in education"
]

results = []
for topic in topics:
    state = {
        "messages": [HumanMessage(content=f"Create a tweet about {topic}")],
        **DEFAULT_INITIAL_STATE
    }
    
    result = graph.invoke(state)
    final_tweet = get_final_tweet(result)
    results.append((topic, final_tweet))
    
    print(f"Topic: {topic}")
    print(f"Tweet: {final_tweet}")
    print("-" * 50)
```

#### Generation in Different Languages
```python
languages = ["ru", "en"]
topic = "Artificial intelligence in education"

for lang in languages:
    state = {
        "messages": [HumanMessage(content=topic)],
        "language": lang,
        **DEFAULT_INITIAL_STATE
    }
    
    result = graph.invoke(state)
    print(f"Language: {lang}")
    print(f"Tweet: {get_final_tweet(result)}")
```

### Integration with Other Systems

#### Wrapper Function
```python
def generate_tweet(topic: str, language: str = "ru", 
                  quality_threshold: float = 0.78) -> dict:
    """
    Generates a tweet for the given topic
    
    Args:
        topic: Topic for the tweet
        language: Language ("ru" or "en")  
        quality_threshold: Minimum quality threshold
        
    Returns:
        dict: Result with tweet and metrics
    """
    from main import graph
    from config import DEFAULT_INITIAL_STATE
    
    state = {
        "messages": [HumanMessage(content=topic)],
        "language": language,
        "quality_threshold": quality_threshold,
        **DEFAULT_INITIAL_STATE
    }
    
    result = graph.invoke(state)
    
    return {
        "tweet": get_final_tweet(result),
        "score": result.get("best_score", 0),
        "reason": "accepted" if not result.get("needs_revision") else "max_iters",
        "candidates": result.get("candidates", []),
        "steps": result.get("steps", []),
        "planned_steps": result.get("planned_steps", [])
    }

# Usage
result = generate_tweet("Python advantages", "en", 0.85)
print(result["tweet"])
```

#### API Wrapper (Flask Example)
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/generate_tweet', methods=['POST'])
def api_generate_tweet():
    data = request.json
    
    try:
        result = generate_tweet(
            topic=data.get('topic'),
            language=data.get('language', 'ru'),
            quality_threshold=data.get('quality_threshold', 0.78)
        )
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
```

### A/B Testing Prompts

#### Testing Different Temperatures
```python
temperatures = [0.2, 0.4, 0.6, 0.8]
topic = "IT innovations"

for temp in temperatures:
    # Switch temperature
    os.system(f"python model_switcher.py switch generation gpt-4o --temperature {temp}")
    
    # Generate tweet
    result = generate_tweet(topic)
    
    print(f"Temperature: {temp}")
    print(f"Tweet: {result['tweet']}")
    print(f"Score: {result['score']}")
    print("-" * 50)
```

#### Testing Different Models
```python
models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
topic = "Future of machine learning"

for model in models:
    # Switch model
    os.system(f"python model_switcher.py switch generation {model}")
    
    # Generate tweet
    result = generate_tweet(topic)
    
    print(f"Model: {model}")
    print(f"Tweet: {result['tweet']}")
    print(f"Score: {result['score']}")
    print("-" * 50)
```

## 🚨 TROUBLESHOOTING

### Common Problems and Solutions

#### 1. API Key Error
```
Error: OpenAI API key not found
```

**Solution:**
```bash
# Check .env file
cat .env

# Ensure key is correct
echo "OPENAI_API_KEY=sk-..." > .env
```

#### 2. Slow Performance
```
Requests taking too long
```

**Solutions:**
```bash
# 1. Check cache
python cache_manager.py stats

# 2. Increase cache size
python cache_manager.py config --max-size 2000

# 3. Switch to faster model
python model_switcher.py switch generation gpt-4o-mini
```

#### 3. Low Quality Results
```
Tweets not meeting quality threshold
```

**Solutions:**
```bash
# 1. Lower quality threshold
# In .env: QUALITY_SCORE_THRESHOLD=0.7

# 2. Switch to higher quality model
python model_switcher.py switch generation gpt-4o

# 3. Increase max iterations
# In .env: MAX_ITERS_DEFAULT=5
```

#### 4. Validation Errors
```
Input validation failed
```

**Causes and solutions:**
- Topic too long (max 500 characters)
- Suspicious content (HTML, scripts)
- System commands in text

**Check:**
```python
from agents.input_sanitizer import InputSanitizer

sanitizer = InputSanitizer()
clean_topic = sanitizer.sanitize_topic("Your topic")
print(f"Cleaned topic: {clean_topic}")
```

#### 5. Fallback Issues
```
All providers unavailable
```

**Solutions:**
```bash
# 1. Check provider status
python model_switcher.py status

# 2. Add fallback providers
python model_switcher.py fallback generation gpt-3.5-turbo
python model_switcher.py fallback critique gpt-4o-mini

# 3. Check network connection
curl -I https://api.openai.com/v1/models
```

### Production Monitoring

#### Error Logging
```python
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tweet_agent.log'),
        logging.StreamHandler()
    ]
)
```

#### Monitoring Metrics
- Correlation ID coverage (100% of requests should have IDs)
- Cache hit rate (>50% for production)
- Error rate (<5% for production)
- Average response time (<10s for generation)
- Token usage and costs

#### Alerts
Set up alerts for:
- Error rate > 10%
- Response time > 30s
- Cache hit rate < 30%
- API quota usage > 80%

## 📈 PERFORMANCE OPTIMIZATION

### Cache Configuration
```bash
# For high-load systems
python cache_manager.py config --max-size 5000 --ttl 3600

# For development
python cache_manager.py config --max-size 500 --ttl 1800
```

### Optimal Model Selection
- **gpt-4o-mini**: Fast, cheap, good quality
- **gpt-4o**: Slower, expensive, excellent quality
- **gpt-3.5-turbo**: Fastest, economical, basic quality

### Load Balancing
```python
# Distribution by task types
configs = {
    "fast": TweetAgentConfig(model_name="gpt-4o-mini", max_iters=1),
    "quality": TweetAgentConfig(model_name="gpt-4o", max_iters=3),
    "creative": TweetAgentConfig(model_name="gpt-4o", temperature=0.8)
}

def generate_tweet_optimized(topic: str, mode: str = "fast"):
    return generate_tweet_with_config(topic, configs[mode])
```

---

## 🎯 CONCLUSION

This system provides a complete toolkit for enterprise-grade AI tweet generation:

- **Ease of use**: launch with one command
- **Flexibility**: full model and parameter customization  
- **Reliability**: error handling, fallbacks, retry logic
- **Performance**: intelligent caching
- **Monitoring**: full process observability
- **Security**: input validation and sanitization

The system is production-ready with all necessary administration and monitoring tools! 🚀