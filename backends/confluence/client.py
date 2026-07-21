import json
import urllib.error
import urllib.parse
import urllib.request

METADATA_URL = "{base_url}/rest/api/content/{page_id}"
CONTENT_URL = "{base_url}/rest/api/content/{page_id}?expand=body.storage"
TITLE_URL = "{base_url}/rest/api/content" "?spaceKey={space_key}" "&title={title}"


class ConfluenceClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _redirect(self, url):
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.url
        except urllib.error.HTTPError as exc:
            raise ValueError(f"GET {url} failed: {exc.code} {exc.reason}") from exc

    def _get(self, url):
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise ValueError(f"GET {url} failed: {exc.code} {exc.reason}") from exc

    def _put(self, url, data: dict):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url, data=body, headers=self._headers(), method=f"PUT"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise ValueError(f"PUT {url} failed: {exc.code} {exc.reason}") from exc

    def get_metadata(self, page_id: int):
        try:
            get_url = METADATA_URL.format(base_url=self.base_url, page_id=page_id)
            return self._get(get_url)
        except ValueError as exc:
            raise ValueError(f"GET page {page_id} failed: {exc}") from exc

    def get_content(self, page_id: int):
        try:
            get_url = CONTENT_URL.format(base_url=self.base_url, page_id=page_id)
            return self._get(get_url)
        except ValueError as exc:
            raise ValueError(f"GET page {page_id} failed: {exc}") from exc

    def put_content(self, page_id: int, version: int, title: str, xhtml: str):
        url = CONTENT_URL.format(base_url=self.base_url, page_id=page_id)
        data = {
            "version": {"number": version},
            "type": "page",
            "title": title,
            "body": {"storage": {"value": xhtml, "representation": "storage"}},
        }
        try:
            return self._put(url, data)
        except ValueError as exc:
            raise ValueError(f"GET page {page_id} failed: {exc}") from exc

    def search_by_title(self, space_key: str, title: str):
        url = TITLE_URL.format(
            base_url=self.base_url,
            space_key=urllib.parse.quote(space_key),
            title=urllib.parse.quote(title),
        )
        return self._get(url)

    def _resolve_page_id(self, value: str) -> int:
        """Accept a numeric page ID or a Confluence page URL; return the numeric ID."""
        if value.isdigit():
            return int(value)

        try:
            final_url = self._redirect(value)
        except ValueError as exc:
            raise ValueError(f"Could not resolve page URL: {exc}") from exc

        parsed = urllib.parse.urlparse(final_url)
        parts = parsed.path.split("/")
        if len(parts) < 4 or parts[1] != "display":
            raise ValueError(f"Could not extract page from resolved URL: {final_url}")
        space_key = parts[2]
        title = urllib.parse.unquote_plus(parts[3])

        url = TITLE_URL.format(
            base_url=self.base_url,
            space_key=urllib.parse.quote(space_key),
            title=urllib.parse.quote(title),
        )

        try:
            data = self._get(url)
        except ValueError as exc:
            raise ValueError(f"Could not look up page by title: {exc}") from exc

        results = data.get("results", [])
        if not results:
            raise ValueError(f"No page found for space={space_key!r} title={title!r}")
        return results[0]["id"]

    def read_page(self, page: str):
        page_id = self._resolve_page_id(page)
        try:
            resp = self.get_content(page_id)
        except ValueError as exc:
            raise ValueError(f"GET page {page_id} failed: {exc}") from exc
        xhtml = resp["body"]["storage"]["value"]
        return xhtml

    def update_page(self, page: str, title, xhtml_content):
        page_id = self._resolve_page_id(page)
        try:
            data = self.get_metadata(page_id)
        except ValueError as exc:
            raise ValueError(f"GET page {page_id} failed: {exc}") from exc
        current_version = data["version"]["number"]
        title = data["title"]

        result = self.put_content(page_id, current_version + 1, title, xhtml_content)
        new_version = result["version"]["number"]
        return new_version

    def get_noexpand_page(self, page: str):
        page_id = self._resolve_page_id(page)
        try:
            get_url = METADATA_URL.format(base_url=self.base_url, page_id=page_id)
            resp = self._get(get_url)
            return json.loads(resp.read().decode())
        except ValueError as exc:
            raise ValueError(f"GET page {page_id} failed: {exc}") from exc

    def create_page(self, space_key, title, content):
        # Implement logic to create a new page in Confluence using the API
        pass

    def delete_page(self, page_id):
        # Implement logic to delete a page from Confluence using the API
        pass
