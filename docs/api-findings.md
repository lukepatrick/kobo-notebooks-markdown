# Kobo Notebooks API Findings

**Date:** 2026-01-02
**Browser:** Firefox 146.0
**Kobo Region:** us

---

## Authentication

**Method:** Cookie-based

**Required Cookies:**
| Cookie Name | Domain | Purpose |
|-------------|--------|---------|
| `KoboSession` | kobo.com | Primary session token (long hex string) |
| `session` | kobo.com | Contains `userid`, `signature`, and other user data |
| `sessionId` | kobo.com | Session identifier |

**Required Headers:**
| Header Name | Value Pattern |
|-------------|---------------|
| `X-Requested-With` | `XMLHttpRequest` |
| `Accept` | `application/json, text/javascript, */*; q=0.01` |

**Session Duration:** Unknown - appears to persist across browser sessions

---

## Endpoints Discovered

### 1. List Notebooks

```
URL: https://www.kobo.com/us/en/library/notebooks
Method: GET
Response: HTML (server-side rendered)
```

**Note:** No JSON API for listing notebooks. The list is embedded in HTML.

**Parsing Strategy:**
Extract notebook IDs from HTML elements:
```html
<li class="notebook-item-wrapper">
    <a class="notebook-item-detail"
       data-notebook-id="c5d2f819-844a-4f6f-be13-e91b2dc6dc0a"
       data-notebook-can-be-previewed="True">
```

Also available in the HTML:
- `data-notebook-etag` - ETag for caching
- `data-notebook-last-modified-utc` - Last modified timestamp
- Notebook title in `<div class="notebook-title">` > `<p>`

**Pagination:** Not observed (may appear with many notebooks)

---

### 2. Get Notebook Metadata

```
URL: https://www.kobo.com/us/en/Library/GetNotebookMetadata
Method: GET
```

**Query Parameters:**
| Param | Required | Description |
|-------|----------|-------------|
| `notebookId` | Yes | UUID of the notebook |

**Response Format:**
```json
{
  "sl_translate": "",
  "result": "success",
  "data": {
    "Id": "c5d2f819-844a-4f6f-be13-e91b2dc6dc0a",
    "DisplayName": "26Jan",
    "FileSize": "109336",
    "ETag": "\"3eb8e3ef81c393c5a358dde9bed4c516\"",
    "ContentType": "application/vnd.myscript.nebo+text",
    "TotalPages": 1,
    "LastModifiedUtc": "2026-01-02T17:49:31.4957397Z",
    "Tags": {"additionalProp1": "1", "additionalProp2": "1"},
    "ThumbnailFile": null,
    "CanBePreviewed": true
  }
}
```

**ContentType Values:**
- `application/vnd.myscript.nebo+text` - Advanced notebook (has text recognition)
- `application/vnd.myscript.nebo` - Basic notebook (no text, images only)
- `application/vnd.myscript.nebo+raw` - Basic notebook variant

---

### 3. Get Notebook Content (Page)

```
URL: https://www.kobo.com/us/en/Library/GetNotebookContent
Method: GET
```

**Query Parameters:**
| Param | Required | Description |
|-------|----------|-------------|
| `notebookId` | Yes | UUID of the notebook |
| `page` | Yes | 0-indexed page number |
| `etag` | Yes | ETag from metadata (URL-encoded quotes) |

**Response Format:**
```json
{
  "sl_translate": "",
  "result": "success",
  "data": {
    "notebookContent": "<!DOCTYPE html>..."
  }
}
```

The `notebookContent` field contains full HTML with:
- Inline CSS for formatting
- Content in `<div class="block-text">` elements
- Text spans with styling
- Lists, headings, etc.

---

### 4. Get Notebook Thumbnail

```
URL: https://www.kobo.com/us/en/Library/GetNotebookThumbnailImage
Method: GET
```

**Query Parameters:**
| Param | Required | Description |
|-------|----------|-------------|
| `notebookId` | Yes | UUID of the notebook |
| `etag` | Yes | ETag from metadata |

**Response:** Image file (PNG/JPEG)

---

## Sample cURL Commands

### List All Notebooks (HTML)
```bash
curl 'https://www.kobo.com/us/en/library/notebooks' \
  --compressed \
  -H 'Cookie: KoboSession=YOUR_SESSION; session=YOUR_SESSION_DATA'
```

### Get Notebook Metadata
```bash
curl 'https://www.kobo.com/us/en/Library/GetNotebookMetadata?notebookId=c5d2f819-844a-4f6f-be13-e91b2dc6dc0a' \
  --compressed \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Cookie: KoboSession=YOUR_SESSION; session=YOUR_SESSION_DATA'
```

### Get Notebook Content (Page 0)
```bash
curl 'https://www.kobo.com/us/en/Library/GetNotebookContent?notebookId=c5d2f819-844a-4f6f-be13-e91b2dc6dc0a&page=0&etag=%223eb8e3ef81c393c5a358dde9bed4c516%22' \
  --compressed \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Cookie: KoboSession=YOUR_SESSION; session=YOUR_SESSION_DATA'
```

---

## Observations

### Content Structure
- Advanced notebooks return HTML with recognized text
- User-written wikilinks like `[[A calendar of wisdom]]` are preserved in the text
- Content is organized in `<div class="block-text" data-block-id="...">` elements
- Each block contains `<p>` and `<span>` elements with styling

### Bot Detection
- `/Tracking/VerifyHuman` endpoint called on page load
- Sends `{"a":4,"b":0,"c":4}` - likely bot detection payload
- May need to handle this for automation

### Rate Limiting
- Not observed during testing

### Error Responses
- Unknown - need to test with invalid session/IDs

---

## Implementation Notes

### Parsing HTML for Notebook List
```python
# Use BeautifulSoup or similar
# Find all: li.notebook-item-wrapper a[data-notebook-id]
# Extract: data-notebook-id, data-notebook-can-be-previewed
# Find title in: .notebook-title p
```

### Extracting Text from Content HTML
```python
# Parse notebookContent HTML
# Find all: div.block-text
# Extract text from p and span elements
# Preserve structure (headings, lists, paragraphs)
```

### Cookie Extraction
Key cookies to extract from Firefox:
- `KoboSession`
- `session`
- `sessionId`

These are from domain `kobo.com` (and `www.kobo.com`)
