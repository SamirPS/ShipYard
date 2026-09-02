# Exploratory QA with Holo

Can a computer-use agent test whether a developer can actually accomplish a goal without being given a predefined click path?

This project explores that question using **Holo**, from H Company’s and the agent opens **Shipyard**, a fictional cloud dashboard, and is given a developer goal:

> Create a Python project, generate an API key, and inspect the latest deployment logs.

Instead of following hard-coded selectors or a scripted sequence, the agent observes screenshots, decides what to do next, interacts with the interface through Playwright, and performs a short exploratory review before producing a QA report.

---

## What we're building

The demo combines four simple pieces:

```text
qa_agent.py
    |
    | H Company API
    v
Holo computer-use model
    |
    | screenshots + actions
    v
Playwright browser
    |
    v
Shipyard
localhost:5000
    |
    v
Cloudflare Tunnel
```

Shipyard intentionally contains one small developer-experience issue.

The agent is **not told where the issue is**.

Its job is to complete the developer journey and report only problems it can support with evidence from what it observed.

---

## Why exploratory QA?

Traditional browser tests are great when you already know the exact path you want to verify. For example, a deterministic test might say:

```text
click this selector
fill this field
open this tab
assert this text exists
```

But sometimes the more interesting question is:

> Can a user actually accomplish the goal?

In this demo, the test intent is expressed at that level:

```text
Create a Python project,
generate an API key,
and inspect the latest deployment logs.
```

The agent decides how to get there. This does **not** replace deterministic browser testing. Instead, it explores where computer-use agents may complement tools like Playwright for exploratory QA and developer-experience testing.

---

## Repository structure

```text
.
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── app.py
│   ├── templates/
│   └── static/
├── agent/
│   └── qa_agent.py
└── examples/
    └── qa-report.md
```

`app/` contains Shipyard, the application under test.

`agent/` contains the Holo + Playwright exploratory QA loop.

---

## Prerequisites

You'll need:

* Python 3.11+
* an H Company API key
* Cloudflare `cloudflared`
* Chromium installed through Playwright

---

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

Copy the environment file:

```bash
cp .env.example .env
```

Add your H Company API key:

```env
HAI_API_KEY=your_h_company_api_key
```

---

## 1. Run Shipyard

Start the application:

```bash
python app/app.py
```

Shipyard should now be available at:

```text
http://localhost:5000
```

Before running the agent, you can open the URL manually and try the developer journey yourself.

---

## 2. Expose Shipyard with Cloudflare Tunnel

The Holo API needs to interact with a publicly reachable application, so expose the local Flask server using Cloudflare Tunnel.

In another terminal:

```bash
cloudflared tunnel --url http://localhost:5000
```

Cloudflare will return a temporary public URL similar to:

```text
https://example.trycloudflare.com
```

Add it to `.env`:

```env
SHIPYARD_URL=https://example.trycloudflare.com
```

---

## 3. Run the exploratory QA agent

Start the agent:

```bash
python agent/qa_agent.py
```

A Chromium window opens so you can watch the agent interact with Shipyard.

The agent will attempt to:

1. create a Python project;
2. generate an API key;
3. inspect the latest deployment logs;
4. perform a short exploratory review;
5. return an evidence-based QA report.

---

## How the agent loop works

The core loop is simple:

```text
Observe
   ↓
Reason
   ↓
Act
   ↓
Observe again
```

At each step, the script:

1. captures a screenshot of the browser;
2. sends the screenshot and QA objective to Holo;
3. receives a tool call such as `click` or `write`;
4. executes the action with Playwright;
5. captures the new browser state;
6. repeats until Holo returns the final report.

Holo returns click coordinates normalized between `0` and `1000`. The script converts those coordinates back to the actual screenshot dimensions before sending the click to Playwright. To keep the context small, only the most recent screenshots are retained.

---

## The exploratory QA prompt

The primary task is intentionally written as a **user goal**, not a click script.

The agent is told to:

* report only issues it directly observed;
* avoid treating its own navigation mistakes as bugs;
* avoid turning unrelated feature ideas into QA findings;
* distinguish functional bugs from UX friction;
* revisit important state-changing actions before ending the session.

An agent can explore freely, but a QA finding should still be supported by evidence. For example, suggesting that a product *should support deployment history* is a product suggestion. It is not automatically a QA finding unless the missing capability interferes with the developer goal being tested.

---

## What did the agent find?

Shipyard contains one intentional developer-experience issue. When an API key is generated, the full credential is visible.
After navigating away, the developer can return to the API Keys section, but the credential is permanently masked. The problem is not that the key is only shown once.

The UX issue is that the interface does **not warn the developer beforehand** that the credential will only be visible once.
A first-time developer could therefore navigate away without saving it and be forced to revoke and regenerate the key.

The interesting part is that the agent is never told:

```text
There is a problem with the API key flow.
```

It only receives the developer goal and the exploratory QA rules. See [`examples/qa-report.md`](examples/qa-report.md) for an example result.

---

## Why not just use Playwright selectors?

Playwright is still responsible for browser automation in this project. The difference is **where the intent lives**. A deterministic test encodes the path:

```text
click "#new-project"
fill "#project-name"
click "#api-keys"
click "#generate-key"
```

The computer-use agent receives the outcome instead:

```text
Create a Python project,
generate an API key,
and inspect the latest deployment logs.
```

This makes the approach interesting for scenarios where the question is less:

> Did this exact sequence of selectors still work?

and more:

> Could a user successfully accomplish what they came here to do?

---

## Where this approach fits

Computer-use agents are probabilistic. Like a normal user, they can misread an interface, make navigation mistakes, or produce different findings between runs.

