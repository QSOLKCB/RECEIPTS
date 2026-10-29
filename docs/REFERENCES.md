# Technical and methodological references

Documentation checked during development on 30 October 2026 (Australia/Adelaide).

- Slade, T. (2026). Public-evidence audit, v1.1.0:
  https://doi.org/10.5281/zenodo.23759846
- X ID representation and precision:
  https://docs.x.com/fundamentals/x-ids
- Twitter's original Snowflake layout and epoch (historical implementation):
  https://github.com/twitter-archive/snowflake/blob/snowflake-2010/src/main/scala/com/twitter/service/snowflake/IdWorker.scala
- OpenAI structured outputs and their schema limits:
  https://developers.openai.com/api/docs/guides/structured-outputs
- Selected model's documented snapshot and supported endpoints:
  https://developers.openai.com/api/docs/models/gpt-5.4-mini
- GitHub manual workflow execution and default-branch requirement:
  https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
- GitHub workflow permissions:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub Models retirement (30 July 2026; do not use its former inference endpoint):
  https://docs.github.com/en/github-models
- Apache License 2.0:
  https://www.apache.org/licenses/LICENSE-2.0

Action pins were resolved through GitHub's API from these tags:

| Action | Tag | Retrieved commit |
|---|---|---|
| actions/checkout | v6 | d23441a48e516b6c34aea4fa41551a30e30af803 |
| actions/setup-python | v6 | ece7cb06caefa5fff74198d8649806c4678c61a1 |
| actions/upload-artifact | v4 | ea165f8d65b6e75b540449e92b4886f43607fa02 |

Pins improve dependency traceability. They do not certify the absence of security
defects, and maintainers should review upstream updates over time.
