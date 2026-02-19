# Security Advisory

## Dependency Updates - Critical Security Fixes

### Date: 2024-02-19

### Summary
Updated all dependencies with known security vulnerabilities to their patched versions.

---

## Fixed Vulnerabilities

### 1. aiohttp (3.9.1 → 3.13.3)

**CVE Details:**
- **Zip Bomb Vulnerability**: HTTP Parser auto_decompress feature vulnerable to zip bomb attacks
  - Affected: <= 3.13.2
  - Fixed: 3.13.3

- **Denial of Service**: Vulnerable to DoS when parsing malformed POST requests
  - Affected: < 3.9.4
  - Fixed: 3.9.4

- **Directory Traversal**: Vulnerable to directory traversal attacks
  - Affected: >= 1.0.5, < 3.9.2
  - Fixed: 3.9.2

**Impact**: High - Could lead to server compromise or denial of service

---

### 2. fastapi (0.109.0 → 0.109.1)

**CVE Details:**
- **Content-Type Header ReDoS**: Regular expression denial of service via Content-Type header
  - Affected: <= 0.109.0
  - Fixed: 0.109.1

**Impact**: Medium - Could cause server slowdown or denial of service

---

### 3. Pillow (10.2.0 → 10.3.0)

**CVE Details:**
- **Buffer Overflow**: Buffer overflow vulnerability in image processing
  - Affected: < 10.3.0
  - Fixed: 10.3.0

**Impact**: High - Could lead to arbitrary code execution

---

### 4. python-multipart (0.0.6 → 0.0.22)

**CVE Details:**
- **Arbitrary File Write**: File write vulnerability via non-default configuration
  - Affected: < 0.0.22
  - Fixed: 0.0.22

- **Denial of Service**: DoS via malformed multipart/form-data boundary
  - Affected: < 0.0.18
  - Fixed: 0.0.18

- **Content-Type Header ReDoS**: Regular expression denial of service
  - Affected: <= 0.0.6
  - Fixed: 0.0.7

**Impact**: Critical - Could lead to file system compromise or denial of service

---

## Updated Dependencies

```python
# requirements.txt updates
fastapi==0.109.1           # was 0.109.0
aiohttp==3.13.3           # was 3.9.1
Pillow==10.3.0            # was 10.2.0
python-multipart==0.0.22  # was 0.0.6
```

---

## Action Required

### For Existing Installations

If you have already installed the Ollama GUI Command Center, please update your dependencies:

```bash
# Activate your virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart the backend
cd backend
python main.py
```

### For New Installations

No action required - the updated requirements.txt will install patched versions automatically.

---

## Verification

After updating, verify the installed versions:

```bash
pip list | grep -E "aiohttp|fastapi|Pillow|python-multipart"
```

Expected output:
```
aiohttp           3.13.3
fastapi           0.109.1
Pillow            10.3.0
python-multipart  0.0.22
```

---

## Security Best Practices

### Going Forward

1. **Regular Updates**: Check for dependency updates monthly
2. **Security Scanning**: Use tools like `pip-audit` or `safety`
3. **Version Pinning**: Keep dependencies pinned to specific versions
4. **Testing**: Test updates in development before production

### Recommended Security Tools

```bash
# Install security audit tools
pip install pip-audit safety

# Run security audit
pip-audit
safety check

# Check for outdated packages
pip list --outdated
```

---

## Timeline

- **2024-02-19**: Vulnerabilities identified
- **2024-02-19**: Dependencies updated to patched versions
- **2024-02-19**: Security advisory published

---

## References

- [aiohttp Security Advisories](https://github.com/aio-libs/aiohttp/security/advisories)
- [FastAPI Security](https://github.com/tiangolo/fastapi/security/advisories)
- [Pillow Security](https://github.com/python-pillow/Pillow/security/advisories)
- [Python Advisory Database](https://github.com/pypa/advisory-database)

---

## Contact

For security concerns or questions:
- Open an issue: https://github.com/gs-ai/ollama-gui/issues
- Label as: `security`

---

**Status**: All known vulnerabilities patched ✅

**Last Updated**: 2024-02-19
