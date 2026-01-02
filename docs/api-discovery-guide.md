# Kobo Web Portal API Discovery Guide

This guide walks you through capturing the API requests that kobo.com/library/notebooks uses behind the scenes. Once we identify these endpoints, we can implement them in the `kobo-md` tool.

---

## Prerequisites

- A Kobo account with notebooks synced to the cloud
- A modern browser (Firefox or Chrome recommended)
- Access to https://www.kobo.com/us/en/library/notebooks

---

## Step 1: Open Browser DevTools

### Firefox
1. Press `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (Mac)
2. Click the **Network** tab
3. Ensure **Persist Logs** is checked (gear icon or right-click in panel)
4. Check **Disable Cache** to see fresh requests

### Chrome
1. Press `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (Mac)
2. Click the **Network** tab
3. Check **Preserve log** checkbox
4. Check **Disable cache** checkbox

---

## Step 2: Navigate to Notebooks Page

1. With DevTools open, go to: https://www.kobo.com/us/en/library/notebooks
2. Log in if prompted (watch for authentication requests)
3. Wait for the page to fully load

---

## Step 3: Identify Key Requests

In the Network tab, filter by **XHR/Fetch** to see only API calls (not images, CSS, etc.).

### What to Look For

Look for requests that return JSON data. Common patterns:

| Request Type | URL Pattern (examples) | Purpose |
|--------------|------------------------|---------|
| **List notebooks** | `/api/notebooks`, `/library/notebooks/list` | Returns array of notebook metadata |
| **Notebook details** | `/api/notebooks/{id}`, `/notebook/{id}` | Returns single notebook info |
| **Export/Download** | `/api/notebooks/{id}/export`, `/download` | Returns notebook content |
| **Authentication** | `/auth`, `/token`, `/session` | Login/session management |

### Filtering Tips

- Type `notebook` in the filter box to narrow results
- Type `api` to find API endpoints
- Click **XHR** or **Fetch** button to hide non-API requests

---

## Step 4: Examine a Request

Click on any promising request to see details:

### Headers Tab

Record these values:

```
REQUEST URL: ___________________________________

REQUEST METHOD: GET / POST / PUT / DELETE

REQUEST HEADERS (copy all that look important):
- Authorization: ___________________________________
- Cookie: ___________________________________
- X-Kobo-*: ___________________________________
- Content-Type: ___________________________________
- Accept: ___________________________________
- User-Agent: ___________________________________
```

### Response Tab

- Click **Response** or **Preview** to see the returned data
- If it's JSON, note the structure

### Cookies Tab

- Note any cookies being sent with the request
- Look for session tokens, auth tokens, or user IDs

---

## Step 5: Capture Authentication Flow

### If Already Logged In

1. Look for requests with `Authorization` header or session cookies
2. Check for tokens in cookies like:
   - `KoboSession`
   - `auth_token`
   - `access_token`
   - `__Secure-*` cookies

### Capture Login Flow (Optional)

1. Log out of Kobo
2. Clear the Network log
3. Log back in
4. Watch for:
   - POST to `/auth/login` or similar
   - Response containing tokens
   - Redirect after successful auth

---

## Step 6: Test Notebook Operations

Perform these actions while watching Network tab:

### Action 1: Load Notebooks List

1. Refresh the notebooks page
2. Find the request that returns the list of notebooks
3. Record the endpoint and response structure

**Record:**
```
ENDPOINT: ___________________________________
METHOD: ___________________________________
RESPONSE STRUCTURE:
{

}
```

### Action 2: View a Notebook

1. Click on a specific notebook
2. Find the request that loads notebook details
3. Note how the notebook ID is passed (URL param, query string, etc.)

**Record:**
```
ENDPOINT: ___________________________________
METHOD: ___________________________________
NOTEBOOK ID FORMAT: ___________________________________
RESPONSE STRUCTURE:
{

}
```

### Action 3: Export a Notebook

1. Click the export/download button on a notebook
2. Choose a format (Text preferred, or HTML)
3. Watch for:
   - Request that initiates export
   - Request that downloads the file (may be a redirect)

**Record:**
```
EXPORT INITIATE ENDPOINT: ___________________________________
EXPORT FORMATS AVAILABLE: ___________________________________
DOWNLOAD ENDPOINT: ___________________________________
RESPONSE TYPE: (file download, JSON with URL, etc.)
```

---

## Step 7: Export Captured Data

### Option A: Copy as cURL (Recommended)

1. Right-click on a request
2. Select **Copy** > **Copy as cURL**
3. Save to a text file

This captures the full request including all headers, which we can convert to Python.

### Option B: Export HAR File

1. Right-click anywhere in the Network panel
2. Select **Save all as HAR with content**
3. Save the `.har` file

HAR files contain all requests and can be parsed programmatically.

### Option C: Manual Notes

Fill in this template for each important endpoint:

```yaml
endpoint_name: "list_notebooks"
url: "https://www.kobo.com/..."
method: "GET"
headers:
  Authorization: "Bearer ..."
  Cookie: "..."
query_params:
  - name: "..."
    value: "..."
response_type: "application/json"
response_example: |
  {
    "notebooks": [...]
  }
```

---

## Step 8: Cookie Extraction Details

If authentication uses cookies, we need to know which ones:

### Firefox Cookie Location
```
~/.mozilla/firefox/[profile]/cookies.sqlite
```

### Chrome Cookie Location
```
~/.config/google-chrome/Default/Cookies        # Linux
~/Library/Application Support/Google/Chrome/Default/Cookies  # Mac
%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies  # Windows
```

### Important Cookies to Note

| Cookie Name | Domain | Purpose |
|-------------|--------|---------|
| | | |
| | | |
| | | |

---

## What We Need to Implement

After your investigation, we need:

### 1. Authentication Method
- [ ] Cookie names required for authenticated requests
- [ ] Or: Bearer token format and how to obtain it
- [ ] Session expiry behavior

### 2. List Notebooks Endpoint
- [ ] Full URL
- [ ] Required headers
- [ ] Response format (JSON structure)
- [ ] Pagination mechanism (if any)

### 3. Export/Download Endpoint
- [ ] Full URL with parameters
- [ ] Export format options (text, html, pdf)
- [ ] How download is triggered (direct file vs. async job)

### 4. Rate Limiting
- [ ] Any observed rate limits
- [ ] Retry-after headers

---

## Reporting Template

After investigation, create a file `docs/api-findings.md` with your discoveries:

```markdown
# Kobo Notebooks API Findings

Date: YYYY-MM-DD
Browser: Firefox/Chrome version X

## Authentication

**Method:** Cookie-based / Bearer token / Other
**Required Cookies/Headers:**
- ...

## Endpoints Discovered

### List Notebooks
- URL:
- Method:
- Headers:
- Response:

### Get Notebook Details
- URL:
- Method:
- Response:

### Export Notebook
- URL:
- Method:
- Formats:
- Response:

## Sample cURL Commands

### List notebooks
```bash
curl '...'
```

### Export notebook
```bash
curl '...'
```

## Notes/Observations

- ...
```

---

## Troubleshooting

### No API Requests Visible

The page might use server-side rendering. Try:
1. Look for embedded JSON in the HTML (`<script>` tags with data)
2. Check if data is in `window.__INITIAL_STATE__` or similar
3. The page may not have a separate API (all HTML-rendered)

### CAPTCHA Blocking

If you encounter CAPTCHA:
1. Complete it manually in the browser
2. Note that automation will be challenging
3. We may need to use browser-cookie3 to extract post-CAPTCHA session

### Requests Not Showing

1. Ensure DevTools was open BEFORE navigating
2. Check that "Persist logs" / "Preserve log" is enabled
3. Try refreshing the page

---

## Next Steps

Once you've completed this investigation:

1. Document findings in `docs/api-findings.md`
2. Implement the endpoints in `src/kobo_md/kobo/client.py`
3. Set up cookie extraction in `src/kobo_md/auth/cookies.py`

See `docs/api-findings.md` for an example of documented API discoveries.
