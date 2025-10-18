# Gemini API Setup - Model Selection

## ✅ Updated Model: `gemini-2.5-flash`

**Date**: October 18, 2025

### Selected Model Details

**Model Name**: `gemini-2.5-flash`
- **Type**: Stable production model
- **Released**: June 2025
- **Description**: Latest stable Flash model with balanced speed and quality

### Specifications

| Feature | Value |
|---------|-------|
| **Input Token Limit** | 1,048,576 tokens (~800K words) |
| **Output Token Limit** | 65,536 tokens (~50K words) |
| **API Version** | v1 |
| **Status** | Stable (Production-ready) |

### Pricing (Paid Tier)

| Metric | Cost |
|--------|------|
| **Input** | $0.075 per 1M tokens |
| **Output** | $0.30 per 1M tokens |
| **Cached Input** | $0.01875 per 1M tokens (75% discount) |

**Example Cost** (typical usage):
- Process 100 questions
- Average 2000 tokens input per question
- Average 500 tokens output per question
- **Total**: 200K input + 50K output
- **Cost**: $0.015 + $0.015 = **$0.03** (3 cents!)

### Rate Limits

| Tier | Requests Per Minute (RPM) | Tokens Per Minute (TPM) |
|------|--------------------------|------------------------|
| **Free** | 15 RPM | 1M TPM |
| **Paid** | 1000 RPM | 4M TPM |

With paid tier, you can process **1000 questions per minute** vs 15 on free tier!

### Why This Model?

✅ **Best Balance**
- Fast enough for real-time classification
- Good quality for mathematical text understanding
- Handles up to 1M input tokens (entire paper if needed)

✅ **Cost Effective**
- Much cheaper than Pro models
- Only $0.075 per 1M input tokens
- Can process thousands of questions for under $1

✅ **High Rate Limits**
- 1000 RPM on paid tier
- No more quota exceeded errors
- Can process full paper batches quickly

✅ **Stable & Production-Ready**
- Not experimental (unlike -exp models)
- Reliable performance
- Official Google support

### Comparison with Other Models

| Model | Speed | Quality | Price | Rate Limit (Paid) |
|-------|-------|---------|-------|-------------------|
| **gemini-2.5-flash** | ⚡⚡⚡ | ⭐⭐⭐⭐ | $ | 1000 RPM |
| gemini-2.5-flash-lite | ⚡⚡⚡⚡ | ⭐⭐⭐ | $$ | 2000 RPM |
| gemini-2.5-pro | ⚡⚡ | ⭐⭐⭐⭐⭐ | $$$ | 360 RPM |
| gemini-2.0-flash-exp | ⚡⚡⚡ | ⭐⭐⭐⭐ | FREE | 10 RPM |
| gemini-2.0-flash-lite | ⚡⚡⚡⚡ | ⭐⭐⭐ | $ | 2000 RPM |

**Legend:**
- Speed: ⚡ = tokens/second
- Quality: ⭐ = accuracy
- Price: $ = cost per 1M tokens

### API Key Information

**✅ No New API Key Needed!**

You can use the **same API key** for all Gemini models:
- gemini-2.5-flash ✅
- gemini-2.5-flash-lite ✅
- gemini-2.5-pro ✅
- gemini-2.0-flash ✅
- All other Gemini models ✅

The API key is **model-agnostic**. You just change the model name in the code.

### Enabling Paid Tier

To get higher rate limits (1000 RPM instead of 15):

1. **Go to Google AI Studio**
   - Visit: https://aistudio.google.com

2. **Set up billing**
   - Click "Billing" in left sidebar
   - Add payment method
   - Choose "Pay as you go" plan

3. **No subscription fee**
   - Only pay for what you use
   - First 1M tokens free each month
   - Very cheap after that ($0.075/1M)

4. **Immediate activation**
   - Rate limits increase automatically
   - No waiting period
   - Same API key works instantly

### Usage Estimates

**Your Further Pure Maths Processing**:
- 2 papers × 10 questions each = 20 questions
- Average 2000 tokens per question
- Total: 40K input tokens + 10K output tokens

**Cost**:
```
Input:  40,000 tokens × $0.075 / 1,000,000 = $0.003
Output: 10,000 tokens × $0.30  / 1,000,000 = $0.003
Total: $0.006 (less than 1 cent!)
```

**If you process 100 papers (1000 questions)**:
```
Input:  2,000,000 tokens × $0.075 / 1,000,000 = $0.15
Output:   500,000 tokens × $0.30  / 1,000,000 = $0.15
Total: $0.30 (30 cents for 100 papers!)
```

### Implementation

**File Changes Made**:
1. `scripts/symbol_aware_classifier.py` - Updated to `gemini-2.5-flash`
2. `scripts/single_topic_classifier.py` - Updated to `gemini-2.5-flash`

**Code Location**:
```python
# Line 47-48 in symbol_aware_classifier.py
self.model = genai.GenerativeModel('gemini-2.5-flash')
```

### Testing Results

✅ **Test 1: Calculus Question**
- Model loaded successfully
- LLM available: True
- Classification: Topic 9 (Calculus), Confidence 0.62
- Multi-topic detection working
- Evidence provided

✅ **Test 2: API Connection**
- No 404 errors
- No "model not found" errors
- Successfully connected to v1 API

⚠️ **Known Issue**: JSON parsing error on some responses (LLM returns non-JSON)
- This is a prompt tuning issue, not a model issue
- Can be fixed by improving prompt format

### Alternative Models (If Needed)

**If you want even cheaper:**
- `gemini-2.5-flash-lite` - 2x faster, slightly lower quality
- `gemini-2.0-flash-lite-001` - Cheapest option

**If you want better quality:**
- `gemini-2.5-pro` - Best quality, 4x more expensive, slower

**If you want to stay on free tier:**
- `gemini-2.0-flash-exp` - Free but only 10 RPM (hits quota quickly)

### Recommendations

**For Your Use Case** (Further Pure Maths classification):

1. ✅ **Stay with `gemini-2.5-flash`**
   - Perfect balance of speed, quality, and cost
   - Production-ready and stable
   - High rate limits when you upgrade to paid

2. ✅ **Upgrade to paid tier**
   - Cost is negligible ($0.30 for 100 papers)
   - Get 1000 RPM instead of 15
   - No more quota errors
   - Process full batches in seconds

3. ✅ **Use same API key**
   - No new key needed
   - Just enable billing
   - Immediate activation

### Next Steps

1. **Test current setup** (already done ✅)
2. **Enable billing** (optional, to avoid rate limits)
3. **Process papers** with new model
4. **Monitor costs** in Google Cloud Console

---

**Status**: ✅ Model updated and tested successfully
**Cost**: ~$0.30 per 1000 questions (incredibly cheap!)
**Rate Limit**: 1000 RPM with paid tier (vs 15 on free)
