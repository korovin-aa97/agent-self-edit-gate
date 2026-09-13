# Protected CI receipt verification

Copy [`verify-receipts.yml`](verify-receipts.yml) into
`.github/workflows/verify-selfedit-receipts.yml` on the protected default branch.
The workflow definition comes from that branch, checks out the pull request's
proposed merge without credentials, installs the exact released verifier, and
runs `verify-receipts` with current-file verification enabled.

For the result to be independent evidence:

- use CODEOWNERS plus branch protection or a ruleset to require trusted review
  for the workflow, `selfedit-policy.toml`, and the receipt-journal anchor;
- keep the verifier version and the previously accepted journal head or journal
  bytes outside the agent's write authority;
- review the Git diff as well as the receipt result; allowed content can still
  be unsafe even when its receipts are valid; and
- do not add steps that execute code from the pull request. The
  `pull_request_target` event can expose trusted context, so this example grants
  only `contents: read`, checks out without credentials, and runs only the
  released verifier against repository data.

If an agent can edit the workflow, policy, verifier pin, and journal anchor, it
can manufacture a new internally consistent history. In that setup the same
command is useful diagnostics, not independent evidence.

The command deliberately omits `--no-current-files`. It therefore verifies the
receipt chain, the policy hash recorded by each operation, and the current hash
of every committed target.
