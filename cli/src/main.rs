// Apache-2.0. Rust handles invocation; Python owns evidence and scoring semantics.
use std::collections::HashSet;
use std::env;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::{self, Command};

const HELP: &str = "RECEIPTS — public-evidence audit control surface

Usage: receipts [--root DIR] [--python EXECUTABLE] COMMAND [ARGUMENTS]

Commands:
  snowflake ID                   Decode a classic Snowflake ID (JSON)
  utc TIMESTAMP                  Normalize a timestamp with a known offset (JSON)
  receipt FILE [OPTIONS]         Hash a researcher-acquired public capture (JSON)
  style FILE                     Summarize supplied writing samples (JSON)
  funding FILE [OPTIONS]         Select explicit direct paid edges (JSON)
  verify                         Verify the preserved four-model checkpoint
  review report --run DIR --review FILE --output DIR
                                 Aggregate human action reviews offline
  experiment prepare|report ...  Freeze repeated comparisons or report runs offline
  eval prepare --output DIR      Prepare paired requests without model calls
  eval run --model ID --output DIR --allow-paid
                                 Run an explicitly authorized paid experiment

Options before COMMAND:
  --root DIR                     Trusted RECEIPTS checkout (default: current directory)
  --python EXECUTABLE             Python 3.10+ executable (default: python3; python on Windows)
  -h, --help                     Show help without starting Python
  -V, --version                  Show control-surface version

Use 'receipts COMMAND --help' for command options.
Relative input/output paths are relative to your current directory, not --root.
Metadata JSON, backend diagnostics, streams and exit codes are passed through.
Evaluation results are saved as JSON artifacts; progress is not a JSON stream.
No inference is performed by help, metadata, verification, review, experiment or eval prepare.
";

const EVAL_HELP: &str = "Usage: receipts [GLOBAL OPTIONS] eval prepare|run [OPTIONS]

  --output DIR                   Required fresh artifact directory; never overwritten
  --model ID                     Required for run; prepare uses the Python default if omitted
  --suite VERSION                v0.1 (default), v0.2 claims, v0.3 actions, v0.4 complex evidence
  --cases N                      1..16 cases, two calls each (default: 16)
  --seed N                       Unsigned integer for case selection and call order (default: 42)
  --max-output-tokens N           256..2048 per call (default: 1200)
  --allow-paid                   Required for run; forbidden for prepare

prepare always uses --dry-run and removes OPENAI_API_KEY from the child environment.
run requires both --model and --allow-paid and inherits OPENAI_API_KEY only then.
This flag records operator intent, not independent proof of authorization.
No secret values belong on the command line. There are no retries or overwrites.
";

const REVIEW_HELP: &str =
    "Usage: receipts [GLOBAL OPTIONS] review report --run DIR --review FILE --output DIR

Read a completed v0.3/v0.4 run and a human-completed copy of action-review-template.json.
Validate record bindings and aggregate declared judgments into a fresh directory
outside the preserved run. Pending reviews stay pending; no automatic judge,
collection or model calls. OPENAI_API_KEY is removed from the backend environment.
Optional --expected-run-sha256 HEX compares a previously retained run digest.
A match is not a signature, authenticated human review or truth certification.
";

const EXPERIMENT_HELP: &str = "Usage: receipts [GLOBAL OPTIONS] experiment prepare|report [OPTIONS]

prepare --model ID --repeats N --notes FILE --output DIR
  Optional: --seed N (default 42), --max-output-tokens N (default 1200)
  Locks all 16 v0.4 cases, both prompts and 2..5 repeats. No inference.
report --plan FILE --runs FILE --expected-plan-sha256 HEX --output DIR
  Checks all planned repeat slots and writes separate comparison artifacts.

Use fresh output directories. Retain the plan digest independently before runs.
Notes record selection decisions, budget basis and pending review; they confer no
spending authority. Counts/bounds do not certify truth or general model quality.
Both operations remove OPENAI_API_KEY from the backend environment.
";

// Values are argv entries, never interpolated into source or a shell command.
// -I ignores PYTHONPATH/current-directory imports; -S disables site customization.
const BOOTSTRAP: &str = r#"import sys
if sys.version_info < (3, 10):
    sys.exit('receipts: Python 3.10 or later is required')
import runpy
kind, target = sys.argv[1:3]
sys.argv = [target] + sys.argv[3:]
if kind == 'module':
    source = sys.argv.pop(1)
    sys.path.insert(0, source)
    runpy.run_module(target, run_name='__main__')
else:
    runpy.run_path(target, run_name='__main__')
"#;

#[derive(Debug)]
enum Action {
    Help(String),
    Version,
    Metadata(Vec<OsString>),
    Verify,
    Evaluate { paid: bool, args: Vec<OsString> },
    Review(Vec<OsString>),
    Experiment { prepare: bool, args: Vec<OsString> },
}

#[derive(Debug)]
struct Options {
    root: PathBuf,
    python: OsString,
    action: Action,
}

fn take_value(args: &[OsString], index: &mut usize, flag: &str) -> Result<OsString, String> {
    *index += 1;
    let value = args
        .get(*index)
        .ok_or_else(|| format!("{flag} requires a value"))?;
    if value.is_empty() || value.to_string_lossy().starts_with('-') {
        return Err(format!(
            "{flag} requires a value; use an explicit path for names starting with '-'"
        ));
    }
    Ok(value.clone())
}

fn help_for(command: &str) -> String {
    match command {
        "snowflake" => "Usage: receipts [GLOBAL OPTIONS] snowflake ID\nID stays a string; the Python backend validates the supported layout.\n".into(),
        "utc" => "Usage: receipts [GLOBAL OPTIONS] utc TIMESTAMP\nAn explicit timezone offset is required.\n".into(),
        "receipt" => "Usage: receipts [GLOBAL OPTIONS] receipt FILE --url HTTPS_URL\n  --retrieved-at TIMESTAMP --locator TEXT --access-basis public_without_login\nPublic access is researcher-attested; hashing does not authenticate content.\n".into(),
        "style" => "Usage: receipts [GLOBAL OPTIONS] style FILE\nFILE is a JSON post list. Results are descriptive, not authorship attribution.\n".into(),
        "funding" => "Usage: receipts [GLOBAL OPTIONS] funding FILE --payer ENTITY --payee ENTITY\nFILE is a JSON edge list. Only explicit direct paid edges are selected.\n".into(),
        "verify" => "Usage: receipts [GLOBAL OPTIONS] verify\nVerifies the preserved 2026-10-30 checkpoint without network access.\n".into(),
        "eval" => EVAL_HELP.into(),
        "review" => REVIEW_HELP.into(),
        "experiment" => EXPERIMENT_HELP.into(),
        _ => HELP.into(),
    }
}

fn evaluate(args: &[OsString]) -> Result<Action, String> {
    let mode = args
        .first()
        .and_then(|a| a.to_str())
        .ok_or("eval requires prepare or run")?;
    let paid = match mode {
        "prepare" => false,
        "run" => true,
        _ => return Err("eval requires prepare or run".into()),
    };
    if args.len() == 2 && (args[1] == "--help" || args[1] == "-h") {
        return Ok(Action::Help(EVAL_HELP.into()));
    }
    let mut seen = HashSet::new();
    let mut forwarded = Vec::new();
    let mut index = 1;
    while index < args.len() {
        let flag = args[index]
            .to_str()
            .ok_or("evaluation option names must be UTF-8")?;
        if !matches!(
            flag,
            "--model"
                | "--suite"
                | "--output"
                | "--cases"
                | "--seed"
                | "--max-output-tokens"
                | "--allow-paid"
        ) {
            return Err("unknown evaluation option; see 'receipts eval --help'".into());
        }
        if !seen.insert(flag.to_owned()) {
            return Err(format!("duplicate evaluation option: {flag}"));
        }
        if flag == "--allow-paid" {
            if !paid {
                return Err("--allow-paid is not valid for eval prepare".into());
            }
        } else {
            let value = take_value(args, &mut index, flag)?;
            if flag == "--suite"
                && value != "v0.1"
                && value != "v0.2"
                && value != "v0.3"
                && value != "v0.4"
            {
                return Err("--suite must be v0.1, v0.2, v0.3 or v0.4".into());
            }
            if matches!(flag, "--cases" | "--seed" | "--max-output-tokens") {
                let n = value
                    .to_str()
                    .and_then(|s| s.parse::<u64>().ok())
                    .ok_or_else(|| format!("{flag} requires an unsigned integer"))?;
                if (flag == "--cases" && !(1..=16).contains(&n))
                    || (flag == "--max-output-tokens" && !(256..=2048).contains(&n))
                {
                    return Err(format!("{flag} is outside the documented bounds"));
                }
            }
            if flag == "--model" && value.to_str().is_none() {
                return Err("--model must be UTF-8".into());
            }
            forwarded.push(OsString::from(flag));
            forwarded.push(value);
        }
        index += 1;
    }
    if !seen.contains("--output") {
        return Err("eval requires --output DIR".into());
    }
    if paid && (!seen.contains("--model") || !seen.contains("--allow-paid")) {
        return Err("eval run requires an explicit --model and --allow-paid; use eval prepare for offline work".into());
    }
    Ok(Action::Evaluate {
        paid,
        args: forwarded,
    })
}

fn review(args: &[OsString]) -> Result<Action, String> {
    if args.first().and_then(|a| a.to_str()) != Some("report") {
        return Err("review requires report; see 'receipts review --help'".into());
    }
    if args.len() == 2 && (args[1] == "--help" || args[1] == "-h") {
        return Ok(Action::Help(REVIEW_HELP.into()));
    }
    let mut seen = HashSet::new();
    let mut index = 1;
    while index < args.len() {
        let flag = args[index]
            .to_str()
            .ok_or("review option names must be UTF-8")?;
        if !matches!(
            flag,
            "--run" | "--review" | "--output" | "--expected-run-sha256"
        ) {
            return Err("unknown review option; see 'receipts review --help'".into());
        }
        if !seen.insert(flag.to_owned()) {
            return Err(format!("duplicate review option: {flag}"));
        }
        let value = take_value(args, &mut index, flag)?;
        if flag == "--expected-run-sha256" {
            let digest = value.to_str().ok_or("run digest must be lowercase hex")?;
            if digest.len() != 64
                || !digest
                    .bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            {
                return Err("run digest must be 64 lowercase hex characters".into());
            }
        }
        index += 1;
    }
    if !["--run", "--review", "--output"]
        .iter()
        .all(|flag| seen.contains(*flag))
    {
        return Err("review report requires --run DIR, --review FILE and --output DIR".into());
    }
    Ok(Action::Review(args.to_vec()))
}

fn experiment(args: &[OsString]) -> Result<Action, String> {
    let prepare = match args.first().and_then(|value| value.to_str()) {
        Some("prepare") => true,
        Some("report") => false,
        _ => return Err("experiment requires prepare or report".into()),
    };
    if args.len() == 2 && (args[1] == "--help" || args[1] == "-h") {
        return Ok(Action::Help(EXPERIMENT_HELP.into()));
    }
    let required: &[&str] = if prepare {
        &["--model", "--repeats", "--notes", "--output"]
    } else {
        &["--plan", "--runs", "--expected-plan-sha256", "--output"]
    };
    let mut seen = HashSet::new();
    let mut index = 1;
    while index < args.len() {
        let flag = args[index]
            .to_str()
            .ok_or("experiment option names must be UTF-8")?;
        if !(required.contains(&flag)
            || prepare && matches!(flag, "--seed" | "--max-output-tokens"))
        {
            return Err("unknown experiment option; see 'receipts experiment --help'".into());
        }
        if !seen.insert(flag.to_owned()) {
            return Err(format!("duplicate experiment option: {flag}"));
        }
        let value = take_value(args, &mut index, flag)?;
        if matches!(flag, "--repeats" | "--seed" | "--max-output-tokens") {
            let n = value
                .to_str()
                .and_then(|s| s.parse::<u64>().ok())
                .ok_or_else(|| format!("{flag} requires an unsigned integer"))?;
            if (flag == "--repeats" && !(2..=5).contains(&n))
                || (flag == "--max-output-tokens" && !(256..=2048).contains(&n))
            {
                return Err(format!("{flag} is outside the documented bounds"));
            }
        }
        if flag == "--model" && value.to_str().is_none() {
            return Err("--model must be UTF-8".into());
        }
        if flag == "--expected-plan-sha256" {
            let digest = value.to_str().ok_or("plan digest must be lowercase hex")?;
            if digest.len() != 64
                || !digest
                    .bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            {
                return Err("plan digest must be 64 lowercase hex characters".into());
            }
        }
        index += 1;
    }
    if !required.iter().all(|flag| seen.contains(*flag)) {
        return Err("missing experiment options; see 'receipts experiment --help'".into());
    }
    Ok(Action::Experiment {
        prepare,
        args: args.to_vec(),
    })
}

fn parse(args: Vec<OsString>) -> Result<Options, String> {
    let mut root = PathBuf::from(".");
    let mut python = OsString::from(if cfg!(windows) { "python" } else { "python3" });
    let mut seen = HashSet::new();
    let mut index = 0;
    while index < args.len() {
        let name = args[index]
            .to_str()
            .ok_or("command and option names must be UTF-8")?;
        match name {
            "--root" | "--python" => {
                if !seen.insert(name.to_owned()) {
                    return Err(format!("duplicate global option: {name}"));
                }
                let value = take_value(&args, &mut index, name)?;
                if name == "--root" {
                    root = PathBuf::from(value);
                } else {
                    python = value;
                }
            }
            "--help" | "-h" if index + 1 == args.len() => {
                return Ok(Options {
                    root,
                    python,
                    action: Action::Help(HELP.into()),
                });
            }
            "--version" | "-V" if index + 1 == args.len() => {
                return Ok(Options {
                    root,
                    python,
                    action: Action::Version,
                });
            }
            "snowflake" | "utc" | "receipt" | "style" | "funding" | "verify" | "eval"
            | "review" | "experiment" => {
                let rest = &args[index + 1..];
                let action = if rest.len() == 1 && (rest[0] == "--help" || rest[0] == "-h") {
                    Action::Help(help_for(name))
                } else if name == "eval" {
                    evaluate(rest)?
                } else if name == "review" {
                    review(rest)?
                } else if name == "experiment" {
                    experiment(rest)?
                } else if name == "verify" {
                    if !rest.is_empty() {
                        return Err("verify accepts no command arguments".into());
                    }
                    Action::Verify
                } else {
                    Action::Metadata(args[index..].to_vec())
                };
                return Ok(Options {
                    root,
                    python,
                    action,
                });
            }
            _ => {
                return Err(
                    "unknown command/global option; see 'receipts --help' (global options precede the command)"
                        .into(),
                );
            }
        }
        index += 1;
    }
    Ok(Options {
        root,
        python,
        action: Action::Help(HELP.into()),
    })
}

fn backend(options: &Options) -> Result<Command, String> {
    let root = options
        .root
        .canonicalize()
        .map_err(|_| "cannot open checkout; pass --root DIR")?;
    let source = root.join("src");
    for file in ["__init__.py", "__main__.py", "runner.py"] {
        if !source.join("receipts").join(file).is_file() {
            return Err("selected root is not a RECEIPTS checkout (missing Python backend)".into());
        }
    }
    // An executable name/path only, never an interpreter plus shell arguments.
    let mut command = Command::new(&options.python);
    command.args(["-I", "-S", "-c", BOOTSTRAP]);
    match &options.action {
        Action::Metadata(args) => {
            command.args(["module", "receipts"]).arg(&source).args(args);
            command.env_remove("OPENAI_API_KEY");
        }
        Action::Evaluate { paid, args } => {
            command
                .args(["module", "receipts.runner"])
                .arg(&source)
                .arg("--root")
                .arg(&root)
                .args(args);
            if !paid {
                command.arg("--dry-run").env_remove("OPENAI_API_KEY");
            }
        }
        Action::Review(args) => {
            command
                .args(["module", "receipts.action_review"])
                .arg(&source)
                .args(args);
            command.env_remove("OPENAI_API_KEY");
        }
        Action::Experiment { prepare, args } => {
            command
                .args(["module", "receipts.experiment"])
                .arg(&source)
                .args(args);
            if *prepare {
                command.arg("--root").arg(&root);
            }
            command.env_remove("OPENAI_API_KEY");
        }
        Action::Verify => {
            let script = root.join("experiments/preservation-2026-10-30/verify.py");
            if !script.is_file() {
                return Err("selected checkout has no supported preservation verifier".into());
            }
            command.arg("script").arg(script).arg("--root").arg(&root);
            command.env_remove("OPENAI_API_KEY");
        }
        _ => return Err("internal command routing error".into()),
    }
    // Inherit cwd and streams: data paths retain the caller's meaning; no buffering/reformatting.
    Ok(command)
}

fn run() -> Result<i32, String> {
    let options = parse(env::args_os().skip(1).collect())?;
    match &options.action {
        Action::Help(text) => {
            print!("{text}");
            Ok(0)
        }
        Action::Version => {
            println!(
                "receipts-cli {} (Python backend required)",
                env!("CARGO_PKG_VERSION")
            );
            Ok(0)
        }
        _ => {
            let mut command = backend(&options)?;
            let launch_error =
                "could not start Python; use --python with a Python 3.10+ executable";
            #[cfg(unix)]
            {
                use std::os::unix::process::CommandExt;
                // Keep the caller's PID: killing it must stop the Python backend,
                // including when a timeout targets only this process.
                let _error = command.exec();
                // Successful exec never returns. Keep failure diagnostics free of argv/env.
                Err(launch_error.into())
            }
            #[cfg(not(unix))]
            {
                let status = command.status().map_err(|_| launch_error)?;
                Ok(status.code().unwrap_or(1))
            }
        }
    }
}

fn main() {
    match run() {
        Ok(code) => process::exit(code),
        Err(message) => {
            eprintln!("receipts: {message}");
            process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsStr;

    fn options(args: &[&str]) -> Result<Options, String> {
        parse(args.iter().map(OsString::from).collect())
    }

    #[test]
    fn paid_intent_cannot_be_implied_by_an_api_key_or_default_model() {
        for args in [
            vec!["eval", "run", "--output", "run"],
            vec!["eval", "run", "--output", "run", "--model", "some-model"],
            vec!["eval", "run", "--output", "run", "--allow-paid"],
        ] {
            assert!(options(&args).is_err());
        }
        assert!(matches!(
            options(&[
                "eval",
                "run",
                "--output",
                "run",
                "--model",
                "some-model",
                "--allow-paid"
            ])
            .unwrap()
            .action,
            Action::Evaluate { paid: true, .. }
        ));
    }

    #[test]
    fn prepare_cannot_accept_paid_or_arbitrary_runner_flags() {
        for flag in [
            "--allow-paid",
            "--root",
            "--dry-run",
            "--endpoint",
            "--api-key",
        ] {
            assert!(options(&["eval", "prepare", "--output", "run", flag]).is_err());
        }
    }

    #[test]
    fn calls_and_tokens_stay_bounded() {
        for (flag, value) in [
            ("--cases", "0"),
            ("--cases", "17"),
            ("--max-output-tokens", "255"),
            ("--max-output-tokens", "2049"),
            ("--seed", "NaN"),
        ] {
            assert!(options(&["eval", "prepare", "--output", "run", flag, value]).is_err());
        }
        assert!(options(&[
            "eval",
            "prepare",
            "--output",
            "run",
            "--cases",
            "16",
            "--max-output-tokens",
            "2048",
            "--seed",
            "0"
        ])
        .is_ok());
    }

    #[test]
    fn ambiguous_duplicate_options_are_rejected() {
        assert!(options(&["--root", ".", "--root", ".", "verify"]).is_err());
        assert!(options(&[
            "eval",
            "run",
            "--model",
            "one",
            "--model",
            "two",
            "--output",
            "run",
            "--allow-paid"
        ])
        .is_err());
    }

    #[test]
    fn suite_selection_is_explicit_and_allowlisted() {
        for suite in ["v0.1", "v0.2", "v0.3", "v0.4"] {
            assert!(options(&["eval", "prepare", "--output", "run", "--suite", suite]).is_ok());
        }
        assert!(options(&["eval", "prepare", "--output", "run", "--suite", "../v0.1"]).is_err());
        assert!(options(&[
            "eval", "prepare", "--output", "run", "--suite", "v0.1", "--suite", "v0.2"
        ])
        .is_err());
    }

    #[test]
    fn review_requires_complete_allowlisted_arguments() {
        let args = [
            "review",
            "report",
            "--run",
            "run",
            "--review",
            "review.json",
            "--output",
            "report",
        ];
        assert!(matches!(options(&args).unwrap().action, Action::Review(_)));
        assert!(options(&args[..6]).is_err());
        for extra in [
            vec!["--allow-paid"],
            vec!["--model", "x"],
            vec!["--run", "other"],
            vec!["--expected-run-sha256", "bad"],
        ] {
            let mut invalid = args.to_vec();
            invalid.extend(extra);
            assert!(options(&invalid).is_err());
        }
        let digest = "a".repeat(64);
        let mut pinned = args.to_vec();
        pinned.extend(["--expected-run-sha256", &digest]);
        assert!(options(&pinned).is_ok());
        assert!(matches!(
            options(&["review", "report", "--help"]).unwrap().action,
            Action::Help(_)
        ));
    }

    #[test]
    fn experiment_operations_are_bounded_offline_and_require_complete_inputs() {
        let args = [
            "experiment",
            "prepare",
            "--model",
            "stub",
            "--repeats",
            "2",
            "--notes",
            "notes.md",
            "--output",
            "plan",
        ];
        assert!(matches!(
            options(&args).unwrap().action,
            Action::Experiment { prepare: true, .. }
        ));
        for extra in [
            vec!["--allow-paid"],
            vec!["--model", "other"],
            vec!["--root", "other"],
            vec!["--max-output-tokens", "2049"],
        ] {
            let mut invalid = args.to_vec();
            invalid.extend(extra);
            assert!(options(&invalid).is_err());
        }
        let mut invalid = args.to_vec();
        invalid[5] = "6";
        assert!(options(&invalid).is_err());
        assert!(options(&args[..8]).is_err());
        assert!(options(&["experiment", "run"]).is_err());
        assert!(options(&[
            "experiment",
            "report",
            "--plan",
            "plan.json",
            "--runs",
            "index.json",
            "--output",
            "report"
        ])
        .is_err());
        let digest = "b".repeat(64);
        assert!(matches!(
            options(&[
                "experiment",
                "report",
                "--plan",
                "plan.json",
                "--runs",
                "index.json",
                "--output",
                "report",
                "--expected-plan-sha256",
                &digest
            ])
            .unwrap()
            .action,
            Action::Experiment { prepare: false, .. }
        ));
    }

    #[test]
    fn help_and_version_need_no_checkout_or_python() {
        assert!(matches!(
            options(&["--root", "/missing", "--python", "missing", "--help"])
                .unwrap()
                .action,
            Action::Help(_)
        ));
        assert!(matches!(
            options(&["eval", "run", "--help"]).unwrap().action,
            Action::Help(_)
        ));
        assert!(matches!(
            options(&["--version"]).unwrap().action,
            Action::Version
        ));
    }

    #[test]
    fn path_and_metadata_values_remain_separate_os_arguments() {
        let opts = options(&[
            "--root",
            "checkout with spaces",
            "--python",
            "python path",
            "receipt",
            "$(touch marker).txt",
            "--locator",
            "line 1; echo no",
        ])
        .unwrap();
        assert_eq!(opts.root, PathBuf::from("checkout with spaces"));
        assert_eq!(opts.python, OsStr::new("python path"));
        if let Action::Metadata(args) = opts.action {
            assert_eq!(args[1], OsStr::new("$(touch marker).txt"));
            assert_eq!(args[3], OsStr::new("line 1; echo no"));
        } else {
            panic!("expected metadata arguments");
        }
    }
}
