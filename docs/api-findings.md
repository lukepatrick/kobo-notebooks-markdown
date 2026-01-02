# Kobo Notebooks API Findings

> Fill in this template after following `api-discovery-guide.md`

**Date:** YYYY-MM-DD
**Browser:** Firefox/Chrome version X
**Kobo Region:** us/ca/other

---

## Authentication

**Method:** Cookie-based / Bearer token / Other

**Required Cookies:**
| Cookie Name | Domain | Example Value (redacted) |
|-------------|--------|--------------------------|
| | | |
| | | |

**Required Headers:**
| Header Name | Value Pattern |
|-------------|---------------|
| | |
| | |

**Session Duration:** (how long before expiry?)

---

## Endpoints Discovered

### 1. List Notebooks

```
URL:
Method: GET / POST
```

**Request Headers:**
```http

```

**Query Parameters:**
| Param | Required | Description |
|-------|----------|-------------|
| | | |

**Response Format:**
```json

```

**Pagination:** (if applicable)

---

### 2. Get Notebook Details

```
URL:
Method: GET
```

**URL Parameters:**
- `{notebook_id}` - format:

**Response Format:**
```json

```

---

### 3. Export/Download Notebook

```
URL:
Method: GET / POST
```

**Available Formats:**
- [ ] Text (.txt)
- [ ] HTML
- [ ] Word (.docx)
- [ ] PDF
- [ ] PNG/JPEG
- [ ] ZIP

**Export Flow:**
1.
2.
3.

**Response:** (direct file download / JSON with download URL / async job ID)

---

## Sample cURL Commands

### Authenticate / Validate Session
```bash

```

### List All Notebooks
```bash

```

### Get Notebook Details
```bash

```

### Export Notebook as Text
```bash

```

---

## Observations

### Rate Limiting
-

### Error Responses
-

### Quirks/Notes
-

---

## Blockers / Issues Encountered

-

---

## Raw HAR File

If you exported a HAR file, note its location:
```
Path:
```
