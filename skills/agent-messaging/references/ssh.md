# Message across devices over SSH

Use an existing authorized SSH login to run the chosen native route **on the receiver's device**. SSH access alone does not establish access to its live agent. Keep the receiver's control endpoint local; no LAN listener or broker is needed.

## Resolve both ends

- Confirm the receiver's SSH destination/account, native environment, installed skill/runtime paths and live socket or Codex home/thread. Set `TARGET_*` in the remote process; an SSH shell does not inherit the running agent's environment. Obtain values from the receiver rather than forwarding the sender's session variables.
- Use the actual remote shell and IPC environment. Native Windows, WSL and containers are distinct; logging into the host does not enter the receiver's environment automatically. Check executable paths when the SSH shell's `PATH` differs.
- For replies, include the sender's device/session and a return SSH destination plus native route usable **from the receiver**. SSH aliases are machine-local; `a` on B need not mean the same host as `a` on A. Establish both directions before promising back-and-forth collaboration. Keep tokens in an authorized remote environment/secret channel, out of messages and command arguments.
- For code collaboration, identify each checkout/revision and divide file or worktree ownership. SSH does not synchronize working trees; exchange commits or patches explicitly.

## Send

Read the chosen native route for its prerequisites. This example assumes POSIX shells on both ends and the skill plus Node.js installed on B. Replace the destination, paths and thread ID with receiver-confirmed values:

```bash
ssh -T b 'TARGET_CODEX_ENDPOINT= TARGET_CODEX_HOME="/receiver/codex-home" TARGET_THREAD_ID="receiver-thread-id" node "/installed/agent-messaging/scripts/steer-codex.mjs" -' < message.txt
```

The file is local to A; the command and paths are on B. Pass message bytes through stdin without a pseudo-terminal (`-T`), not by interpolating message text into the remote shell command. Quote substituted paths/IDs for that shell. For [CC inbox](claude-code.md), use `send-claude.mjs -` with the receiver's `TARGET_CC_SOCKET` and required token supplied remotely.

For [queue](codex-queue.md), run its local-receiver command on B with B's explicit `CODEX_HOME`; an already reachable native `--remote` endpoint can instead be used directly. SSH does not change steer/queue/start/interrupt semantics or make a new resumed process control the original session.

Interpret the native route's result as usual. A dropped SSH connection or missing reply does not prove non-delivery; check the receiver before resending.

Transport references: [OpenSSH `ssh(1)`](https://man.openbsd.org/ssh.1), [Windows SSH shell configuration](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration#configuring-the-default-shell-for-openssh-in-windows).
