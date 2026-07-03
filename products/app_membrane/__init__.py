"""Product A — App membrane (WebAssembly hard guarantee).

Runs untrusted code as a WebAssembly guest with zero ambient authority; the only
channel to the outside world is a host-granted capability import, mediated by the
shared core.guard engine. What the host does not grant does not exist for the guest.
"""
