# User Ideas

>>> **CRITICAL**: AGENTS MUST NOT MODIFY THIS FILE! <<<

This file contains issues and ideas noted by the user.

## Pi handoff context

- In Pi, when connecting to the inter-agent session, add a message to the context so that the agent knows that it has been connected to the session and doesn't need to use the `whoami` command. (This should not prompt a reply from the agent; it should just be part of the "next turn" when the user prompts again.)
  - *May* also be able to tweak the user's personal inter-agent handoff sub-skill so that the `whoami` check is no longer *required* to perform a handoff.
    - Make sure the user tests this behavior manually if any changes are made!

## Startup error handling

- Show a better error message if running the `start` script when a session has already started.
  - It currently crashes with a decent error message at the end, but the whole process could be a little cleaner.
