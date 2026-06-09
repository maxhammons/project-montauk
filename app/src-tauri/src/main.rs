use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn project_root() -> Result<PathBuf, String> {
    if let Ok(root) = env::var("MONTAUK_PROJECT_ROOT") {
        return Ok(PathBuf::from(root));
    }
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .ok_or_else(|| "could not infer project root".to_string())
}

fn read_json(path: &Path) -> Result<Value, String> {
    if !path.exists() {
        return Ok(Value::Null);
    }
    let raw = fs::read_to_string(path).map_err(|err| err.to_string())?;
    serde_json::from_str(&raw).map_err(|err| err.to_string())
}

fn read_jsonl(path: &Path, limit: usize) -> Result<Vec<Value>, String> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let raw = fs::read_to_string(path).map_err(|err| err.to_string())?;
    let mut rows = Vec::new();
    for line in raw.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        rows.push(serde_json::from_str(trimmed).map_err(|err| err.to_string())?);
    }
    if rows.len() > limit {
        Ok(rows[rows.len() - limit..].to_vec())
    } else {
        Ok(rows)
    }
}

fn latest_signal(root: &Path) -> Result<Value, String> {
    let signals = root.join("signals");
    if !signals.exists() {
        return Ok(Value::Null);
    }
    let mut files = fs::read_dir(signals)
        .map_err(|err| err.to_string())?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().and_then(|v| v.to_str()) == Some("json"))
        .collect::<Vec<_>>();
    files.sort();
    match files.last() {
        Some(path) => read_json(path),
        None => Ok(Value::Null),
    }
}

fn python_path(root: &Path) -> PathBuf {
    let venv = root.join(".venv/bin/python");
    if venv.exists() {
        venv
    } else {
        PathBuf::from("python3")
    }
}

fn launch_agent_label(job_key: &str) -> String {
    format!("com.project-montauk.{}", job_key.replace('_', "-"))
}

fn launch_agent_path(job_key: &str) -> Result<PathBuf, String> {
    let home = env::var("HOME").map_err(|_| "HOME is not available".to_string())?;
    Ok(PathBuf::from(home)
        .join("Library/LaunchAgents")
        .join(format!("{}.plist", launch_agent_label(job_key))))
}

fn validate_job_key(root: &Path, job_key: &str) -> Result<(), String> {
    if !job_key
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '-' || ch == '_')
    {
        return Err("invalid scheduler job key".to_string());
    }

    let scheduler = read_json(&root.join("runs/scheduler/config.json"))?;
    if scheduler
        .get("jobs")
        .and_then(|jobs| jobs.get(job_key))
        .is_none()
    {
        return Err(format!("unknown scheduler job key: {}", job_key));
    }
    Ok(())
}

fn user_id() -> Option<String> {
    let output = Command::new("id").arg("-u").output().ok()?;
    if !output.status.success() {
        return None;
    }
    let id = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if id.is_empty() {
        None
    } else {
        Some(id)
    }
}

fn launch_agent_loaded(label: &str) -> Option<bool> {
    let uid = user_id()?;
    let target = format!("gui/{}/{}", uid, label);
    let output = Command::new("launchctl")
        .arg("print")
        .arg(target)
        .output()
        .ok()?;
    Some(output.status.success())
}

fn run_json_command(root: &Path, args: &[&str]) -> Result<Value, String> {
    let output = Command::new(python_path(root))
        .args(args)
        .current_dir(root)
        .output()
        .map_err(|err| err.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if stderr.is_empty() {
            stdout.trim().to_string()
        } else {
            stderr
        });
    }
    serde_json::from_str(&stdout).map_err(|err| err.to_string())
}

fn read_scheduler_status(root: &Path) -> Result<Value, String> {
    let scheduler_script = root.join("scripts/ops/scheduler.py");
    let script = scheduler_script
        .to_str()
        .ok_or_else(|| "scheduler path is not valid UTF-8".to_string())?;
    run_json_command(root, &[script, "status", "--json"])
}

fn read_launch_agents_status(root: &Path) -> Result<Value, String> {
    let agent_script = root.join("scripts/ops/install_launch_agent.py");
    let script = agent_script
        .to_str()
        .ok_or_else(|| "LaunchAgent path is not valid UTF-8".to_string())?;
    run_json_command(root, &[script, "--all-enabled", "--status", "--json"])
}

fn read_doctor_report(root: &Path) -> Result<Value, String> {
    let doctor_script = root.join("scripts/ops/doctor.py");
    let script = doctor_script
        .to_str()
        .ok_or_else(|| "doctor path is not valid UTF-8".to_string())?;
    run_json_command(root, &[script, "--json"])
}

fn read_app_update_status(root: &Path) -> Result<Value, String> {
    let update_script = root.join("scripts/ops/app_update.py");
    let script = update_script
        .to_str()
        .ok_or_else(|| "app update path is not valid UTF-8".to_string())?;
    run_json_command(root, &[script, "--json"])
}

fn read_research_runs(root: &Path) -> Result<Value, String> {
    let runs_dir = root.join("runs/research_queue/runs");
    if !runs_dir.exists() {
        return Ok(json!({ "runs": [], "run_count": 0 }));
    }
    let mut files = fs::read_dir(runs_dir)
        .map_err(|err| err.to_string())?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().and_then(|v| v.to_str()) == Some("json"))
        .collect::<Vec<_>>();
    files.sort();
    let start = files.len().saturating_sub(30);
    let mut runs = Vec::new();
    for path in &files[start..] {
        let mut payload = read_json(path)?;
        if let Some(object) = payload.as_object_mut() {
            object.insert("record_path".to_string(), json!(path));
        }
        runs.push(payload);
    }
    Ok(json!({ "runs": runs, "run_count": runs.len() }))
}

fn valid_notification_event_type(event_type: &str) -> bool {
    matches!(
        event_type,
        "champion_blocked"
            | "champion_changed"
            | "data_quality_failed"
            | "data_stale"
            | "job_failed"
            | "live_holdout_drift"
            | "manual_review_required"
            | "replacement_candidate"
            | "signal_changed"
            | "signal_snapshot_conflict"
            | "viz_build_failed"
    )
}

#[tauri::command]
fn read_status() -> Result<Value, String> {
    let root = project_root()?;
    let operations = root.join("runs/operations");
    let scheduler = root.join("runs/scheduler/config.json");
    let launch_agent = launch_agent_status("daily".to_string())
        .unwrap_or_else(|err| json!({"job_key": "daily", "error": err}));
    let launch_agents =
        read_launch_agents_status(&root).unwrap_or_else(|err| json!({"error": err}));
    let scheduler_detail = read_scheduler_status(&root).unwrap_or_else(|err| json!({"error": err}));
    let doctor =
        read_doctor_report(&root).unwrap_or_else(|err| json!({"status": "unknown", "error": err}));
    Ok(json!({
        "project_root": root,
        "latest_operation": read_json(&operations.join("latest.json"))?,
        "latest_signal": latest_signal(&root)?,
        "recent_events": read_jsonl(&operations.join("events.jsonl"), 40)?,
        "live_holdout": read_json(&operations.join("live_holdout.json"))?,
        "governance": read_json(&operations.join("governance.json"))?,
        "strategy_review": read_json(&operations.join("strategy_review.json"))?,
        "maintenance_status": read_json(&operations.join("maintenance_status.json"))?,
        "family_leaderboard": read_json(&root.join("runs/family_confidence_leaderboard.json"))?,
        "leaderboard": read_json(&root.join("spike/leaderboard.json"))?,
        "notifications": read_json(&operations.join("notifications.json"))?,
        "notification_state": read_json(&operations.join("notification_state.json"))?,
        "research_queue": read_json(&root.join("runs/research_queue/queue.json"))?,
        "research_runs": read_research_runs(&root)?,
        "top_strategies": read_json(&operations.join("top_strategies.json")).unwrap_or(Value::Null),
        "scheduler": read_json(&scheduler)?,
        "scheduler_detail": scheduler_detail,
        "launch_agents": launch_agents,
        "app_update": read_app_update_status(&root).unwrap_or_else(|err| json!({"error": err})),
        "doctor": doctor,
        "launch_agent": launch_agent
    }))
}

#[tauri::command]
fn run_job(job: String) -> Result<Value, String> {
    let root = project_root()?;
    let output = Command::new(python_path(&root))
        .arg(root.join("scripts/ops/run_job.py"))
        .arg("--job")
        .arg(job)
        .arg("--json")
        .current_dir(&root)
        .output()
        .map_err(|err| err.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).to_string());
    }
    serde_json::from_str(&stdout).map_err(|err| err.to_string())
}

#[tauri::command]
fn scan_notifications() -> Result<Value, String> {
    let root = project_root()?;
    let notification_script = root.join("scripts/ops/notifications.py");
    let script = notification_script
        .to_str()
        .ok_or_else(|| "notifications path is not valid UTF-8".to_string())?;
    run_json_command(&root, &[script, "--scan", "--json"])
}

#[tauri::command]
fn send_notifications() -> Result<Value, String> {
    let root = project_root()?;
    let notification_script = root.join("scripts/ops/notifications.py");
    let script = notification_script
        .to_str()
        .ok_or_else(|| "notifications path is not valid UTF-8".to_string())?;
    run_json_command(&root, &[script, "--send", "--json"])
}

#[tauri::command]
fn set_notification_preference(event_type: String, enabled: bool) -> Result<Value, String> {
    if !valid_notification_event_type(&event_type) {
        return Err(format!("unknown notification event type: {}", event_type));
    }
    let root = project_root()?;
    let notification_script = root.join("scripts/ops/notifications.py");
    let script = notification_script
        .to_str()
        .ok_or_else(|| "notifications path is not valid UTF-8".to_string())?;
    run_json_command(
        &root,
        &[
            script,
            "--set-event",
            &event_type,
            "--enabled",
            if enabled { "true" } else { "false" },
            "--json",
        ],
    )
}

#[tauri::command]
fn scheduler_status() -> Result<Value, String> {
    let root = project_root()?;
    read_scheduler_status(&root)
}

#[tauri::command]
fn doctor_report() -> Result<Value, String> {
    let root = project_root()?;
    read_doctor_report(&root)
}

#[tauri::command]
fn set_scheduler_job(job_key: String, enabled: bool) -> Result<Value, String> {
    let root = project_root()?;
    validate_job_key(&root, &job_key)?;
    let scheduler_script = root.join("scripts/ops/scheduler.py");
    let script = scheduler_script
        .to_str()
        .ok_or_else(|| "scheduler path is not valid UTF-8".to_string())?;
    let action = if enabled { "enable" } else { "disable" };
    run_json_command(&root, &[script, action, &job_key, "--json"])?;
    read_scheduler_status(&root)
}

#[tauri::command]
fn research_queue_action(idea_id: String, action: String) -> Result<Value, String> {
    if !idea_id
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '-' || ch == '_')
    {
        return Err("invalid research idea id".to_string());
    }
    if !matches!(
        action.as_str(),
        "approve" | "dismiss" | "pause" | "resume" | "reset"
    ) {
        return Err(format!("unknown research action: {}", action));
    }
    let root = project_root()?;
    let research_script = root.join("scripts/ops/research_queue.py");
    let script = research_script
        .to_str()
        .ok_or_else(|| "research queue path is not valid UTF-8".to_string())?;
    run_json_command(&root, &[script, &action, &idea_id, "--json"])
}

#[tauri::command]
fn enqueue_research_ideas() -> Result<Value, String> {
    let root = project_root()?;
    let research_script = root.join("scripts/ops/research_queue.py");
    let script = research_script
        .to_str()
        .ok_or_else(|| "research queue path is not valid UTF-8".to_string())?;
    run_json_command(&root, &[script, "propose", "--json"])
}

#[tauri::command]
fn strategy_metric_signal(metric: String) -> Result<Value, String> {
    if !matches!(
        metric.as_str(),
        "confidence" | "share_multiple" | "real_share_multiple" | "modern_share_multiple"
    ) {
        return Err(format!("unknown strategy metric: {}", metric));
    }
    let root = project_root()?;
    let review_script = root.join("scripts/ops/strategy_review.py");
    let script = review_script
        .to_str()
        .ok_or_else(|| "strategy review path is not valid UTF-8".to_string())?;
    run_json_command(
        &root,
        &[
            script,
            "--metric",
            &metric,
            "--include-signal",
            "--no-write",
            "--json",
        ],
    )
}

#[tauri::command]
fn start_research_run(idea_id: String) -> Result<Value, String> {
    if !idea_id
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '-' || ch == '_')
    {
        return Err("invalid research idea id".to_string());
    }
    let root = project_root()?;
    let runner_script = root.join("scripts/ops/research_runner.py");
    let script = runner_script
        .to_str()
        .ok_or_else(|| "research runner path is not valid UTF-8".to_string())?;
    run_json_command(&root, &[script, "--idea-id", &idea_id, "--json"])
}

#[tauri::command]
fn launch_agent_status(job_key: String) -> Result<Value, String> {
    let root = project_root()?;
    validate_job_key(&root, &job_key)?;
    let label = launch_agent_label(&job_key);
    let path = launch_agent_path(&job_key)?;
    Ok(json!({
        "job_key": job_key,
        "label": label,
        "path": path,
        "installed": path.exists(),
        "loaded": launch_agent_loaded(&label)
    }))
}

#[tauri::command]
fn manage_launch_agent(job_key: String, action: String) -> Result<Value, String> {
    let root = project_root()?;
    let all_enabled = job_key == "__enabled";
    if !all_enabled {
        validate_job_key(&root, &job_key)?;
    }
    let mut command = Command::new(python_path(&root));
    command
        .arg(root.join("scripts/ops/install_launch_agent.py"))
        .current_dir(&root);

    if all_enabled {
        command.arg("--all-enabled").arg("--json");
    } else {
        command.arg("--job-key").arg(&job_key);
    }

    match action.as_str() {
        "install" => {
            command.arg("--install");
        }
        "load" => {
            command.arg("--load");
        }
        "unload" => {
            command.arg("--unload");
        }
        "uninstall" => {
            command.arg("--uninstall");
        }
        _ => return Err(format!("unknown LaunchAgent action: {}", action)),
    }

    let output = command.output().map_err(|err| err.to_string())?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        return Err(if stderr.is_empty() { stdout } else { stderr });
    }

    if all_enabled {
        return read_launch_agents_status(&root);
    }

    let mut status = launch_agent_status(job_key)?;
    if let Some(object) = status.as_object_mut() {
        object.insert("last_action".to_string(), json!(action));
        object.insert(
            "output".to_string(),
            json!(String::from_utf8_lossy(&output.stdout).trim().to_string()),
        );
    }
    Ok(status)
}

#[tauri::command]
fn open_viz() -> Result<(), String> {
    let root = project_root()?;
    let path = root.join("viz/montauk-viz.html");
    Command::new("open")
        .arg(path)
        .status()
        .map_err(|err| err.to_string())?;
    Ok(())
}

#[tauri::command]
fn read_viz_html() -> Result<String, String> {
    let root = project_root()?;
    let path = root.join("viz/montauk-viz.html");
    fs::read_to_string(path).map_err(|err| err.to_string())
}

#[tauri::command]
fn read_viz_bundle(rebuild: Option<bool>) -> Result<Value, String> {
    let root = project_root()?;
    let bundle_path = root.join("viz/montauk-bundle.json");
    let force_rebuild = rebuild.unwrap_or(false);

    if force_rebuild || !bundle_path.exists() {
        let script = root.join("viz/build_viz.py");
        let output = Command::new(python_path(&root))
            .arg(script)
            .arg("--bundle-only")
            .current_dir(&root)
            .output()
            .map_err(|err| err.to_string())?;
        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            return Err(if stderr.is_empty() { stdout } else { stderr });
        }
    }

    if !bundle_path.exists() {
        return Err(format!(
            "viz bundle missing after build attempt at {}",
            bundle_path.display()
        ));
    }
    read_json(&bundle_path)
}

#[tauri::command]
fn start_maintenance(force: Option<bool>) -> Result<Value, String> {
    let root = project_root()?;
    let py = python_path(&root);
    let script = root.join("scripts/ops/maintenance.py");
    // Manual "Refresh" forces a data pull; the once-per-day gate only applies
    // to the automatic launch refresh.
    let force_refresh = force.unwrap_or(false);

    // Reset the status file so the frontend doesn't show stale data while we boot.
    let status_path = root.join("runs/operations/maintenance_status.json");
    let initial = json!({
        "schema_version": 1,
        "status": "starting",
        "started_utc": null,
        "finished_utc": null,
        "phases": [],
        "current_phase": null,
        "summary": null,
        "error": null,
    });
    if let Some(parent) = status_path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    fs::write(
        &status_path,
        serde_json::to_string_pretty(&initial).unwrap(),
    )
    .map_err(|err| err.to_string())?;

    let mut command = Command::new(py);
    command.arg(script);
    if force_refresh {
        command.arg("--force-refresh");
    }
    command
        .current_dir(&root)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map_err(|err| err.to_string())?;
    Ok(json!({ "status": "started", "force_refresh": force_refresh }))
}

#[tauri::command]
fn read_maintenance_status() -> Result<Value, String> {
    let root = project_root()?;
    read_json(&root.join("runs/operations/maintenance_status.json"))
}

#[tauri::command]
fn read_agent_inbox() -> Result<Value, String> {
    let root = project_root()?;
    read_json(&root.join("runs/operations/agent_inbox.json"))
}

#[tauri::command]
fn read_flip_pressure_history(days: Option<usize>) -> Result<Value, String> {
    let root = project_root()?;
    let signals_dir = root.join("signals");
    if !signals_dir.exists() {
        return Ok(json!({ "points": [] }));
    }
    let mut files: Vec<PathBuf> = fs::read_dir(&signals_dir)
        .map_err(|err| err.to_string())?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().and_then(|v| v.to_str()) == Some("json"))
        .collect();
    files.sort();
    let limit = days.unwrap_or(60);
    let start = files.len().saturating_sub(limit);
    let mut points: Vec<Value> = Vec::new();
    for path in &files[start..] {
        let payload = match read_json(path) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let date = payload
            .get("data_end_date")
            .and_then(|v| v.as_str())
            .map(String::from)
            .or_else(|| path.file_stem().and_then(|s| s.to_str()).map(String::from));
        let confidence = payload
            .pointer("/validation/composite_confidence")
            .and_then(|v| v.as_f64());
        let warnings_count = payload
            .pointer("/validation/warnings")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0);
        let blockers_count = payload
            .get("blockers")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0);
        let signal_changed = payload
            .pointer("/signal_change/changed")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        // Prefer the Monte-Carlo flip likelihood if present; else fall back
        // to the legacy confidence/warning heuristic.
        let likelihood = payload.get("flip_likelihood").and_then(|v| v.as_f64());
        let pressure = if let Some(lk) = likelihood {
            (lk * 100.0).clamp(0.0, 99.0)
        } else {
            let mut pressure = match confidence {
                Some(c) => (1.0 - c) * 100.0,
                None => 48.0,
            };
            pressure += (warnings_count as f64 * 2.0).min(14.0);
            pressure += (blockers_count as f64 * 15.0).min(30.0);
            if signal_changed {
                pressure += 8.0;
            }
            pressure.clamp(0.0, 99.0)
        };
        points.push(json!({
            "date": date,
            "pressure": pressure,
            "confidence": confidence,
            "signal_changed": signal_changed,
        }));
    }
    Ok(json!({ "points": points, "count": points.len() }))
}

#[tauri::command]
fn run_next_research(timeout_seconds: Option<u64>) -> Result<Value, String> {
    let root = project_root()?;
    let queue = read_json(&root.join("runs/research_queue/queue.json"))?;
    let ideas = queue
        .get("ideas")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let next = ideas.into_iter().find(|item| {
        item.get("status")
            .and_then(|v| v.as_str())
            .map(|s| s == "approved")
            .unwrap_or(false)
    });
    let idea = match next {
        Some(value) => value,
        None => {
            return Ok(json!({
                "status": "empty",
                "message": "No approved research ideas in the queue.",
            }))
        }
    };
    let idea_id = idea
        .get("id")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "approved idea has no id".to_string())?
        .to_string();
    if !idea_id
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '-' || ch == '_')
    {
        return Err("invalid research idea id".to_string());
    }

    let runner_script = root.join("scripts/ops/research_runner.py");
    let script = runner_script
        .to_str()
        .ok_or_else(|| "research runner path is not valid UTF-8".to_string())?;
    let timeout = timeout_seconds.unwrap_or(15 * 60).to_string();
    let result = run_json_command(
        &root,
        &[
            script,
            "--idea-id",
            &idea_id,
            "--execute",
            "--timeout-seconds",
            &timeout,
            "--json",
        ],
    )?;
    Ok(json!({
        "status": "ok",
        "idea_id": idea_id,
        "kind": idea.get("kind"),
        "rationale": idea.get("rationale"),
        "result": result,
    }))
}

#[tauri::command]
fn run_all_research(timeout_seconds: Option<u64>) -> Result<Value, String> {
    let root = project_root()?;
    let queue = read_json(&root.join("runs/research_queue/queue.json"))?;
    let approved = queue
        .get("ideas")
        .and_then(|v| v.as_array())
        .map(|ideas| {
            ideas
                .iter()
                .filter(|item| {
                    item.get("status").and_then(|v| v.as_str()) == Some("approved")
                })
                .count()
        })
        .unwrap_or(0);
    if approved == 0 {
        return Ok(json!({
            "status": "empty",
            "message": "No approved research ideas in the queue.",
        }));
    }
    // research_runner.py with no --idea-id executes every approved idea in order.
    let runner_script = root.join("scripts/ops/research_runner.py");
    let script = runner_script
        .to_str()
        .ok_or_else(|| "research runner path is not valid UTF-8".to_string())?;
    let timeout = timeout_seconds.unwrap_or(15 * 60).to_string();
    let result = run_json_command(
        &root,
        &[script, "--execute", "--timeout-seconds", &timeout, "--json"],
    )?;
    Ok(json!({
        "status": "ok",
        "approved_count": approved,
        "result": result,
    }))
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            read_status,
            run_job,
            scan_notifications,
            send_notifications,
            set_notification_preference,
            scheduler_status,
            doctor_report,
            set_scheduler_job,
            research_queue_action,
            enqueue_research_ideas,
            strategy_metric_signal,
            start_research_run,
            launch_agent_status,
            manage_launch_agent,
            open_viz,
            read_viz_html,
            read_viz_bundle,
            run_next_research,
            run_all_research,
            read_agent_inbox,
            start_maintenance,
            read_maintenance_status,
            read_flip_pressure_history
        ])
        .run(tauri::generate_context!())
        .expect("error while running Montauk app");
}
