# HarnessOS repository contract

HarnessOS helps coding agents produce correct, repository-aligned work with clear evidence. It does not replace your chosen coding agent or model provider.

## Understand the request

- Treat the user's stated objective and acceptance criteria as the task. Preserve their intent throughout the work.
- Inspect the repository's own instructions and relevant code before proposing or editing a solution.
- Do not invent requirements, claim unsupported facts, or substitute generic advice for requested work.
- If a missing detail materially changes the solution or creates meaningful risk, ask a short, specific question. Otherwise make a reasonable, reversible assumption and state it.

## Work in the repository

- Follow nearer project instructions and conventions. If instructions conflict, surface the conflict instead of silently choosing the convenient one.
- Select and follow only skills relevant to the task. Read a skill's supporting files when its workflow calls for them.
- Make the requested change, then inspect the resulting diff for accidental or unrelated edits.
- Run the repository's documented checks relevant to the change. Do not claim a check passed unless you observed its result.
- For changes that cannot be fully checked, report exactly what remains unverified and why.

## Report clearly

- Summarize the concrete result and the checks actually run.
- Distinguish observed evidence from inference and intention.
- Keep the response concise, specific, and free of filler, repeated summaries, and unsupported completion claims.
