# Agent Rules

## Git & Privacy Policy
This project is open-source and publicly accessible.
Before committing files or pushing changes to the remote Git repository, the agent MUST:
1. Scan the modified code for any sensitive information (e.g., hardcoded passwords, personal IDs, tokens, internal APIs/IPs, etc.).
2. Inform the user of the review results.
3. Explicitly request and wait for the user's approval before proceeding with `git commit` or `git push`.
