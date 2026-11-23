# Packaging

GitHub Releases are produced when a tag such as `v0.1.0` is pushed.

```bash
git tag v0.1.0
git push origin v0.1.0
```

Release artifacts:

- `ImageLabeler2D-windows-x64.zip`
- `ImageLabeler2D-linux-x64.tar.gz`
- `ImageLabeler2D-macos-arm64.tar.gz` (Apple Silicon)
- `ImageLabeler2D-macos-x64.tar.gz` (Intel Mac)

Workflows:

1. **Release (Primary Platforms)** — Windows x64, Linux x64, macOS arm64 (publishes the GitHub Release).
2. **Release (macOS x64)** — starts after (1) succeeds and appends the Intel Mac package to the same release.

CI (`.github/workflows/ci.yml`) runs `pytest` on Ubuntu, Windows, and macOS for every push and pull request to `main`.

Downloaded macOS builds are unsigned. After extracting, double-click `run_mac.command`, or from that folder:

```bash
xattr -cr .
chmod +x ./ImageLabeler2D
./ImageLabeler2D
```
