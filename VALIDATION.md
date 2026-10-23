# OpenUI 0.2.3 validation

Validated on 23 October 2026 against Agent Zero source revision `ff2a5b9` with framework Python 3.12.4 in an isolated Docker preview. The framework test selection and frontend suite were rerun for publication: **207 passed, 1 skipped** (143 framework/plugin + 64 frontend). The full Agent Zero test suite is not claimed.

## Automated checks

- Frontend typecheck, production build and 64 tests: library contracts, representative rendering and interaction, image handling, templates, chart configurations, host replay/state isolation, and partial Chart.js input at every character boundary.
- 143 framework/plugin tests and one skipped: plugin lifecycle/assets, policy-scoped prompts and tools, chat persistence, mailbox/sender contracts, current-answer streaming and adoption without a separate inference, cancellation, malformed/parallel calls, secret masking, Unicode and native argument streams.
- Both shipped defaults and the missing-setting fallback select `agent_program`. The two visible modes are **Use current answer (streams, no extra call)** and **Generate separately (streams, extra model call)**.
- Installation validates the shipped asset manifest and performs no dependency downloads. The release ZIP was tested through the normal installer with network disabled, including two consecutive install-hook runs.
- npm reported no dependency vulnerabilities in the prior dependency audit. The 0.2.3 publication changes do not change dependency versions.

Reproduce frontend checks from `frontend/` with `npm ci --ignore-scripts`, `npm run typecheck`, `npm test`, and `OPENUI_TELEMETRY_DISABLED=1 npm run build`.

Run backend tests after installing the plugin under `/a0/usr/plugins/openui` in an Agent Zero development environment:

```sh
/opt/venv-a0/bin/python -m pytest -q usr/plugins/openui/tests \
  tests/test_plugin_hook_context.py tests/test_plugin_asset_precedence.py \
  tests/test_tool_policy.py tests/test_persist_chat_log_ids.py \
  tests/test_email_integration_sender.py tests/test_webui_plugin_process_types.py
```

The validation image lacked pytest-asyncio, so those checks used a temporary test-only coroutine runner. It is not needed by the plugin and is not included in the release. A normal development environment should provide the framework's test dependencies, including pytest-asyncio.

## Live checks

- The configured account-backed model selected dashboards, a preference form, an agenda and sourced image results from ordinary requests without an OpenUI keyword. An explicit plain-text arithmetic request stayed text. These are bounded examples, not repeated model benchmarks.
- Default current-answer streaming grew one saved artifact through 192 partial previews before completing it. After fixing a partial-series chart failure, a second chart streamed through ten partial previews and completed without an OpenUI renderer console error. No separate UI-generation inference was requested.
- Required form fields blocked empty submission. Submitted values followed the normal chat path, and persisted state survived restart/reload. Saved artifacts reopened after switching chats and after the component-library update.
- A 390-pixel browser viewport stacked the dashboard and retained working manual carousel navigation. This is a browser breakpoint check, not physical-device testing.
- One explicitly authorized synthetic rich email was accepted by SMTP and found in the connected account's actual IMAP Inbox. Its rich preview retained headings, metrics, a table and a link button. No mailbox contents, credentials or delivery receipts are distributed.

## Limits

- The registry contains 103 general UI and 44 React Email components. Representative tests do not cover every composition or email client. All nine Chart.js configurations have tests; line/bar charts were inspected live.
- Live previews depend on provider argument deltas and an early explicit surface. Buffered providers and unsupported or multiple-call envelopes can finish without a progressive preview. Partial artifacts cannot execute controls or send email.
- Gateway, separate-generation mode with a live model, and local-model generation quality have not been live-validated. Gateway remains optional.
- The preview used limited WebUI/account startup. Full production startup, migrations and scheduled jobs were not acceptance-tested. An unrelated SDK/provider test also failed in a clean core checkout; the full framework suite has not passed here.
- Email supports the existing IMAP/SMTP integration. Exchange/MCP-only mailbox adapters, attachments, provider draft saving, deletion, archiving and mark-read operations are not implemented. Sent-folder copies depend on the provider.
- Generated components are bounded declarative layouts. They cannot execute arbitrary JavaScript, install packages or invoke arbitrary Agent Zero tools. Remote HTTPS images load directly in the visual renderer and may be blocked by the image host; email previews block remote images.

Synthetic screenshots are included under `docs/screenshots/`. Private runtime state, accounts and local environment configuration are excluded.
