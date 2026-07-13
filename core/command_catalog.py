#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A curated catalogue of shell commands a coding agent commonly uses, each with a one- or
two-sentence explanation of what allowing it lets the agent do (and its risk). The control
panel uses this for type-to-search when picking allowed commands, and for the "what can these
do?" info list. Stdlib-only; a plain dict is the single source of truth.

This is not an exhaustive list of every program on a machine — it is the common set a
developer chooses from. Anything not here can still be typed in as a custom entry.
"""

# name -> explanation (kept alphabetical for the info list)
CATALOG = {
    "awk":    "Text-processing language for extracting and transforming columns or lines. Read-only unless it is told to write files.",
    "bash":   "A shell interpreter. Allowing it effectively lets the agent run other programs, so grant it deliberately.",
    "black":  "Python code formatter. Rewrites your .py files in place.",
    "cargo":  "Rust's build and package manager. Compiles code and downloads crates over the network.",
    "cat":    "Print a file's contents to the screen. Read-only.",
    "cd":     "Change the working directory for a command. Harmless.",
    "chmod":  "Change file permissions, including making a file executable.",
    "cmake":  "Build-system generator for C and C++ projects.",
    "cp":     "Copy files or directories.",
    "curl":   "Transfer data over the network. Lets the agent download or send data — a common exfiltration tool, allow with care.",
    "docker": "Build and run containers. Powerful: a container can mount your filesystem and reach the network.",
    "dotnet": "The .NET SDK: build and run C#/F# projects and restore packages from the network.",
    "echo":   "Print text. Harmless.",
    "eslint": "JavaScript/TypeScript linter. Reads your code and can auto-fix files.",
    "false":  "A no-op that always reports failure — used inside shell scripts. Harmless.",
    "find":   "Search for files by name or attributes. Read-only unless combined with -exec or -delete.",
    "gcc":    "The C/C++ compiler.",
    "git":    "Version control. Reads and writes the repository, and reaches the network on clone, pull, and push.",
    "go":     "The Go toolchain: build and test code and fetch modules over the network.",
    "gradle": "Build tool for JVM projects. Runs build scripts, which can execute arbitrary commands.",
    "grep":   "Search for text inside files. Read-only.",
    "head":   "Print the first lines of a file. Read-only.",
    "java":   "Run a compiled Java program. Allowing it lets the agent execute arbitrary Java bytecode.",
    "kill":   "Terminate a running process by its id.",
    "ls":     "List the files in a directory. Read-only.",
    "make":   "Run build recipes from a Makefile — which can execute arbitrary commands.",
    "maven":  "Build and dependency tool for Java (the mvn command). Downloads packages from the network.",
    "mkdir":  "Create a directory.",
    "mv":     "Move or rename files.",
    "mypy":   "Python static type checker. Read-only.",
    "node":   "Run JavaScript with Node.js. Allowing it lets the agent execute arbitrary JavaScript.",
    "npm":    "Node package manager. Installs dependencies from the network and can run package scripts.",
    "npx":    "Run a Node package's binary, downloading it first if needed.",
    "php":    "Run PHP code. Allowing it lets the agent execute arbitrary PHP.",
    "pip":    "Python package installer. Downloads and installs packages from the network.",
    "pip3":   "Python 3 package installer — same as pip. Downloads and installs packages from the network.",
    "pnpm":   "A fast Node package manager, similar to npm.",
    "poetry": "Python dependency and packaging tool. Installs packages from the network.",
    "prettier": "Code formatter for web languages. Rewrites files in place.",
    "pytest": "Run the Python test suite. Executes your test code.",
    "python": "Run Python code. Allowing it lets the agent execute arbitrary Python.",
    "python3": "Run Python 3 code. Allowing it lets the agent execute arbitrary Python.",
    "rm":     "Delete files. Dangerous — keep an 'rm -rf' pattern on the always-blocked list.",
    "ruff":   "A fast Python linter and formatter. Can auto-fix your files.",
    "rustc":  "The Rust compiler.",
    "scp":    "Copy files over SSH to or from a remote host — network access.",
    "sed":    "Stream editor for transforming text; can rewrite files in place.",
    "sh":     "A shell interpreter. Like bash, allowing it effectively permits running other programs.",
    "sort":   "Sort lines of text. Read-only.",
    "ssh":    "Open a shell on a remote host over the network. High-risk and rarely needed for local coding.",
    "tail":   "Print the last lines of a file. Read-only.",
    "tar":    "Create or extract .tar archives.",
    "test":   "A tiny shell built-in used inside scripts to check conditions. Harmless.",
    "touch":  "Create an empty file or update a file's timestamp.",
    "tox":    "Run Python tests across multiple environments.",
    "true":   "A no-op that always reports success — used inside shell scripts. Harmless.",
    "tsc":    "The TypeScript compiler. Reads your code and writes compiled output.",
    "unzip":  "Extract a .zip archive.",
    "wc":     "Count the lines, words, or characters in text. Read-only.",
    "wget":   "Download files over the network — similar to curl.",
    "yarn":   "A Node package manager, similar to npm.",
    "zip":    "Create a .zip archive.",
}


def catalog():
    """-> sorted list of {name, desc} for the UI (info list + autocomplete)."""
    return [{"name": k, "desc": CATALOG[k]} for k in sorted(CATALOG)]
