import re
import secrets

from flask import Flask, abort, redirect, render_template, request, url_for


app = Flask(__name__)

# This demo deliberately keeps its entire state in this process.
state = {
    "project": None,
    "active_api_key": None,
    "pending_api_key": None,
}


def current_project(slug):
    project = state["project"]
    if project is None or project["slug"] != slug:
        abort(404)
    return project


def make_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "python-project"


@app.get("/")
def dashboard():
    return render_template("dashboard.html", project=state["project"])


@app.post("/projects")
def create_project():
    name = request.form.get("name", "").strip()
    runtime = request.form.get("runtime", "Python")
    if not name:
        return render_template(
            "dashboard.html",
            project=state["project"],
            error="Enter a project name.",
        ), 400
    if runtime != "Python":
        return render_template(
            "dashboard.html",
            project=state["project"],
            error="Python is the only runtime available in this demo.",
        ), 400

    project = {
        "name": name,
        "slug": make_slug(name),
        "runtime": "Python",
        "region": "Paris",
        "status": "Running",
    }
    state["project"] = project
    state["active_api_key"] = None
    state["pending_api_key"] = None
    return redirect(url_for("project_overview", slug=project["slug"]))


@app.get("/projects/<slug>")
def project_overview(slug):
    return render_template(
        "project.html",
        project=current_project(slug),
        section="overview",
    )


@app.get("/projects/<slug>/api-keys")
def api_keys(slug):
    return render_template(
        "project.html",
        project=current_project(slug),
        section="api_keys",
        active_api_key=state["active_api_key"],
    )


@app.post("/projects/<slug>/api-keys")
def generate_api_key(slug):
    current_project(slug)
    if state["active_api_key"] is not None:
        return redirect(url_for("api_keys", slug=slug))

    full_key = f"sk_shipyard_demo_{secrets.token_hex(4)}"
    state["active_api_key"] = {
        "masked": "••••••••••••••••••••",
        "created": "Created recently",
    }
    state["pending_api_key"] = full_key
    return redirect(url_for("api_key_created", slug=slug))


@app.get("/projects/<slug>/api-keys/created")
def api_key_created(slug):
    project = current_project(slug)
    full_key = state["pending_api_key"]
    if full_key is None:
        return redirect(url_for("api_keys", slug=slug))

    # Render the secret once, then discard the server-side copy immediately.
    state["pending_api_key"] = None
    response = app.make_response(
        render_template("api_key_created.html", project=project, api_key=full_key)
    )
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.post("/projects/<slug>/api-keys/revoke")
def revoke_api_key(slug):
    current_project(slug)
    state["active_api_key"] = None
    state["pending_api_key"] = None
    return redirect(url_for("api_keys", slug=slug))


@app.get("/projects/<slug>/deployments")
def deployments(slug):
    return render_template(
        "project.html",
        project=current_project(slug),
        section="deployments",
        deployment_date="September 2, 2026",
    )


@app.get("/projects/<slug>/deployments/latest/logs")
def deployment_logs(slug):
    return render_template(
        "deployment_logs.html",
        project=current_project(slug),
    )


@app.get("/reset")
def reset_demo():
    state["project"] = None
    state["active_api_key"] = None
    state["pending_api_key"] = None
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
