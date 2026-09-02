import base64
import json
import os
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from playwright.sync_api import sync_playwright

load_dotenv()

MODEL = "holo3-1-35b-a3b"
MAX_STEPS = 25
VIEWPORT = {"width": 1280, "height": 800}

SHIPYARD_URL = os.environ["SHIPYARD_URL"]

client = OpenAI(
    base_url="https://api.hcompany.ai/v1/",
    api_key=os.environ["HAI_API_KEY"],
)

SYSTEM_PROMPT = """
You are an exploratory QA tester evaluating the developer
experience of a cloud platform called Shipyard.

You are a developer using the application for the first time.

Your goal is to:
1. Create a new Python project.
2. Generate an API key for that project.
3. Find and inspect the latest deployment logs.

Explore naturally. You are not given a predefined click path.

While completing the goal, pay attention to anything that is:
- broken
- confusing
- misleading
- unexpectedly difficult
- likely to cause a developer to make a mistake

QA RULES:
- Only report issues supported by something you directly observed.
- Do not report missing features unless they interfere with the stated goal.
- Do not report your own navigation mistakes as application problems.
- Distinguish functional bugs from UX friction.
- Exploratory does not mean speculative.
- After completing the goal, briefly revisit important stateful or
  irreversible actions and verify that their resulting state is clear
  to a first-time developer.
- Do not invent problems you did not observe.

When you have enough evidence, call the answer tool.

Return:
- Goal completed: YES or NO
- Journey: concise summary
- Findings: for each issue include title, type, evidence, impact, severity
- Overall verdict
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click a visible UI element using normalized coordinates from 0 to 1000.",
            "parameters": {
                "type": "object",
                "properties": {
                    "element": {"type": "string"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                },
                "required": ["element", "x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Type text into the currently focused field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "press_enter": {"type": "boolean"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer",
            "description": "Finish the QA session and return the final report.",
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        },
    },
]


def screenshot_data(page):
    image = page.screenshot(type="png")
    encoded = base64.b64encode(image).decode()
    return image, f"data:image/png;base64,{encoded}"


def keep_recent_screenshots(messages, limit=3):
    count = 0

    for message in reversed(messages):
        content = message.get("content")
        if message.get("role") != "user" or not isinstance(content, list):
            continue

        for item in content:
            if item.get("type") != "image_url":
                continue

            count += 1
            if count > limit:
                item.clear()
                item.update({"type": "text", "text": "[screenshot evicted]"})


def run_action(page, name, args, screenshot):
    if name == "click":
        width, height = Image.open(BytesIO(screenshot)).size
        x = round(args["x"] / 1000 * width)
        y = round(args["y"] / 1000 * height)

        print(f'CLICK: {args["element"]} -> ({x}, {y})')
        page.mouse.click(x, y)

    elif name == "write":
        print(f'WRITE: {args["content"]}')
        page.keyboard.type(args["content"])
        if args.get("press_enter"):
            page.keyboard.press("Enter")

    elif name == "press_key":
        print(f'KEY: {args["key"]}')
        page.keyboard.press(args["key"])

    else:
        raise ValueError(f"Unknown action: {name}")

    page.wait_for_timeout(600)


def run():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(SHIPYARD_URL)
        page.wait_for_load_state("networkidle")

        try:
            for step in range(1, MAX_STEPS + 1):
                print(f"\n--- Step {step} ---")

                screenshot, data_url = screenshot_data(page)

                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "<observation>"},
                            {"type": "image_url", "image_url": {"url": data_url}},
                            {"type": "text", "text": "</observation>"},
                        ],
                    }
                )

                keep_recent_screenshots(messages)

                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="required",
                    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
                )

                message = response.choices[0].message

                if not message.tool_calls:
                    raise RuntimeError("Holo returned no tool call")

                tool_call = message.tool_calls[0]
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                print(f"ACTION: {name}")
                print(json.dumps(args, indent=2))

                messages.append(message.model_dump())

                if name == "answer":
                    report = args["content"]
                    print("\n" + "=" * 60)
                    print("EXPLORATORY QA REPORT")
                    print("=" * 60)
                    print(report)
                    return

                run_action(page, name, args, screenshot)

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f'<tool_output tool="{name}">\n'
                            "Action completed.\n"
                            "</tool_output>"
                        ),
                    }
                )

            raise RuntimeError(f"Agent did not finish after {MAX_STEPS} steps")

        finally:
            browser.close()


if __name__ == "__main__":
    run()
