# Tingly-Agent-Shell

A shell tool for agent and target env (e.g. coding project).
It is also defined as a module to make usage simple.

# Feature
- support open, aka init, a shell
  - allow to set env while init
  - allow to set setup rc for the shell
  - allow to set shell type, like bash, zsh and etc.
- support fork the shell which help open another one and inherit all from parent.
- support execute command in shell, and keep state
  - DO NOT use pexpect since different behavior cross platforms
  - Use basic python module `subprocess` and so on
  - `async` by default
  - support timeout control to avoid agent block
  - internal command wrapper, to detect command execution and exit code
- support api to control shell and fetch information
  - shell env state fetch
  - shell execute result fetch
  - etc.