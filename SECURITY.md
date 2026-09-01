# Security policy

Please report vulnerabilities privately to the repository maintainers rather
than opening a public issue.

Before deployment:

- keep API keys in environment variables or a secret manager;
- use read-only database accounts and restrict database network access;
- run DataFrame agents in an isolated process or container before enabling
  `allow_dangerous_code`;
- restrict CORS and authentication in `src/data2mcp_v2/server/api.py` when the
  service is reachable outside a trusted network;
- treat uploaded documents and model-generated tool calls as untrusted input;
- do not commit `.env`, generated configuration, logs, databases, or outputs.

The demo accepts model credentials in the browser and persists its configuration
to browser storage. Use a dedicated local browser profile for development.
