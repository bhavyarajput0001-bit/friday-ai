import os, re, threading, time
from omniroute import is_available as omni_available, chat as omni_chat, set_key as omni_set_key
from context_engine import context

try:
    from google import genai
    import openai as openai_mod
    from openai import OpenAI
    import anthropic
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROK_API_KEY = os.environ.get("GROK_API_KEY", "")

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None
if ANTHROPIC_API_KEY:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    claude_client = None
if GROK_API_KEY:
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.xai.com/v1")
else:
    grok_client = None

def route_prompt(prompt):
    t = prompt.lower()
    if any(kw in t for kw in ["generate image", "draw", "picture of", "create an image", "paint"]):
        return "IMAGE"
    if any(kw in t for kw in ["write code", "debug", "fix bug", "fix the code", "create a function", "write a script", "write a program", "refactor", "explain this code", "show me code"]):
        return "CODING"
    if any(kw in t for kw in ["remember", "recall", "did i", "did we", "our past", "what did i", "what have we", "memory"]):
        return "MEMORY"
    if any(kw in t for kw in ["research", "analyze", "explain", "compare", "history", "scientific", "why does", "how does", "why is"]):
        return "RESEARCH"
    if any(kw in t for kw in ["recipe", "schedule", "workout", "joke", "story", "write", "email", "routine", "idea", "plan"]):
        return "DAILY"
    return "GENERAL"

def call_gemini(prompt):
    if not gemini_client: return "[Gemini] Key missing."
    try:
        return gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
    except Exception as e:
        return f"[Gemini Error] {e}"

def call_chatgpt(prompt, is_image=False):
    if not openai_client: return "[ChatGPT] Key missing."
    try:
        if is_image:
            r = openai_client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
            return f"[DALL-E URL] {r.data[0].url}"
        r = openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    except Exception as e:
        return f"[ChatGPT Error] {e}"

def call_claude(prompt):
    if not claude_client: return "[Claude] Key missing."
    try:
        r = claude_client.messages.create(model="claude-3-opus-20240229", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
        return r.content[0].text
    except Exception as e:
        return f"[Claude Error] {e}"

def call_grok(prompt):
    if not grok_client: return "[Grok] Key missing."
    try:
        r = grok_client.chat.completions.create(model="grok-beta", messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    except Exception as e:
        return f"[Grok Error] {e}"

def _model_for_category(category):
    mapping = {
        "CODING": "auto/best-coding",
        "RESEARCH": "auto/reasoning",
        "MEMORY": "auto/cheap",
        "DAILY": "auto/cheap",
        "IMAGE": "auto/best-vision",
        "GENERAL": "auto/cheap",
    }
    return mapping.get(category, "auto/cheap")

def _save_memory_async(user, reply):
    def _do():
        try:
            context.save_conversation(user, reply[:2000])
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()

def process_with_brain(prompt, callback):
    category = route_prompt(prompt)
    callback(f"Routing: {category}")

    if omni_available():
        system = context.build_system_prompt(prompt, category)
        model = _model_for_category(category)
        try:
            result = omni_chat(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                model=model,
            )
            if result and result.get("text") and result.get("model") != "error":
                callback(f"OmniRoute [{result.get('model', 'auto')}] ${result.get('cost', 0):.5f}\n{result['text']}")
                _save_memory_async(prompt, result["text"])
                return
        except Exception as e:
            callback(f"[OmniRoute Error] {e}")

    if category == "IMAGE":
        callback("Image mode")
        results = []
        def r1():
            results.append(f"Gemini:\n{call_gemini(f'Describe image concept for: {prompt}')}")
        def r2():
            results.append(f"DALL-E:\n{call_chatgpt(prompt, is_image=True)}")
        threading.Thread(target=r1).start()
        threading.Thread(target=r2).start()
        time.sleep(0.1)
        for r in results: callback(r)
    elif category == "RESEARCH":
        callback("Research mode")
        results = []
        def r1():
            results.append(f"Claude:\n{call_claude(prompt)}")
        def r2():
            results.append(f"Grok:\n{call_grok(prompt)}")
        threading.Thread(target=r1).start()
        threading.Thread(target=r2).start()
        time.sleep(0.1)
        for r in results: callback(r)
    elif category == "DAILY":
        callback(f"ChatGPT:\n{call_chatgpt(prompt)}")
    else:
        callback(f"Gemini:\n{call_gemini(prompt)}")
