# Security Policy

## Overview

StreamCatch takes security seriously. This document outlines our security policies, practices, and how to report vulnerabilities.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| < 1.0   | :x:                |

## Security Features

### Authentication & Authorization
- **Secure Credential Storage**: Google Drive credentials stored in `~/.streamcatch/` with 0600 permissions (owner read/write only)
- **Environment Variable Support**: Credentials can be provided via environment variables
- **No Default Secrets**: Discord RPC and other integrations require explicit configuration

### Input Validation
- **URL Validation**: Strict regex validation for URLs (2048 character limit)
- **SQL Injection Prevention**: Parameterized queries with Google Drive API query escaping
- **Path Traversal Protection**: Path canonicalization and validation for file operations
- **XML External Entity (XXE) Protection**: Uses `defusedxml` for RSS feed parsing
- **Length Limits**: Title (1000 chars), URL (2048 chars), Path (4096 chars) to prevent database bloat

### Network Security
- **SSL Certificate Verification**: Enabled by default (can be disabled per-request if needed)
- **Request Timeouts**: All HTTP requests have configured timeouts
- **Dependency Pinning**: All Python dependencies pinned to specific versions

### File System Security
- **Restricted Permissions**: Config files (0600), credential files (0600), crash logs (0600)
- **Atomic File Writes**: Configuration and credentials written atomically to prevent corruption
- **Symlink Attack Prevention**: Path canonicalization with os.path.realpath()
- **Subprocess Security**: Path validation before executing system commands

### Container Security
- **Non-Root User**: Docker containers run as non-root user streamcatch (UID 1000)
- **Pinned Base Images**: Using python:3.12-slim with pinned system packages
- **Minimal Attack Surface**: Only necessary packages installed

### Build & CI/CD Security
- **Pinned GitHub Actions**: All actions pinned to commit SHAs
- **Dependency Scanning**: safety check runs on all PRs and pushes (blocking)
- **Code Quality Checks**: Black, isort, pylint run on all changes
- **Comprehensive Testing**: 191+ unit tests

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Preferred**: Use [GitHub Security Advisories](https://github.com/yourusername/streamcatch/security/advisories/new) to privately report the issue.
2. **Alternative**: Email security concerns to security@streamcatch.app (replace with actual email).

Please do NOT open a public issue for security vulnerabilities.

**Last Updated**: December 2025
