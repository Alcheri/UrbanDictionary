###
# Copyright (c) 2012-2013, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
# Asynchronous variant of the original UrbanDictionary plugin.
#
###

# Standard library imports
import html
import json
import urllib.error
import urllib.request
from urllib.parse import quote_plus, urlencode, urlsplit
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports
try:
    import aiohttp  # asynchronous HTTP client and server framework
except ImportError as ie:
    raise ImportError(f"Cannot import module: {ie}")

import asyncio  # asynchronous I/O

# Supybot imports
import supybot.log as log
from supybot.commands import getopts, wrap
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

DEFAULT_USER_AGENT = "Limnoria-UrbanDictionary/1.0 (+https://github.com/Alcheri/UrbanDictionary)"
ALLOWED_HOSTS = {"api.urbandictionary.com", "www.urbandictionary.com"}
DEFAULT_MAX_RESPONSE_BYTES = 256 * 1024
MAX_TERM_LENGTH = 120
MAX_REPLY_LENGTH = 1000
MAX_ENTRY_LENGTH = 300
MAX_DEFINITIONS = 10
MAX_TAG_LENGTH = 40
MIN_TIMEOUT = 1
MAX_TIMEOUT = 15
UNSAFE_CONTROL_CHARS_RE = re.compile(
    r"[\x00-\x01\x04-\x0e\x10-\x15\x17-\x1c\x1e\x7f]"
)
WHITESPACE_RE = re.compile(r"\s+")

try:
    from supybot.i18n import PluginInternationalization

    _ = PluginInternationalization("UrbanDictionary")
except ImportError:

    def _(x):
        return x


class UrbanDictionary(callbacks.Plugin):
    """
    Limnoria / Supybot plugin for UrbanDictionary to display definitions
    on http://www.urbandict.com
    """

    threaded = False

    def __init__(self, irc):
        self.__parent = super(UrbanDictionary, self)
        self.__parent.__init__(irc)
        self._cooldowns = {}
        self._cooldown_lock = threading.Lock()

    ######################
    # INTERNAL FUNCTIONS #
    ######################

    def _format_text(
        self,
        string: str,
        color: Optional[str] = None,
        bold: bool = False,
        underline: bool = False,
    ) -> str:
        """Format a string with optional color, bold, and underline."""
        if color:
            string = ircutils.mircColor(string, color)
        if bold:
            string = ircutils.bold(string)
        if underline:
            string = ircutils.underline(string)
        return string

    def _clean_text(
        self,
        value: Any,
        max_length: Optional[int] = None,
        preserve_formatting: bool = True,
    ) -> str:
        """Clean user-facing text while preserving intentional IRC formatting."""
        text = str(value or "")
        if not preserve_formatting:
            text = ircutils.stripFormatting(text)
        text = UNSAFE_CONTROL_CHARS_RE.sub(" ", text)
        text = WHITESPACE_RE.sub(" ", text).strip()
        if max_length is not None and len(text) > max_length:
            text = f"{text[: max(0, max_length - 3)].rstrip()}..."
        return text

    def _validate_term(self, term: str) -> Tuple[bool, str, str]:
        cleaned = self._clean_text(term, max_length=MAX_TERM_LENGTH)
        if not cleaned:
            return False, "", "Please provide a term to search."
        if cleaned != term.strip():
            return False, "", "Search term contains invalid characters."
        if len(cleaned) > MAX_TERM_LENGTH:
            return False, "", "Search term is too long."
        return True, cleaned, ""

    def _clamp_timeout(self, timeout: Any) -> int:
        try:
            value = int(timeout)
        except (TypeError, ValueError):
            return MIN_TIMEOUT
        return max(MIN_TIMEOUT, min(value, MAX_TIMEOUT))

    def _clamp_count(self, value: Any) -> int:
        try:
            count = int(value)
        except (TypeError, ValueError):
            return 1
        return max(1, min(count, MAX_DEFINITIONS))

    def _max_response_bytes(self) -> int:
        try:
            value = int(self.registryValue("maxResponseBytes"))
        except (TypeError, ValueError):
            return DEFAULT_MAX_RESPONSE_BYTES
        return max(1024, min(value, DEFAULT_MAX_RESPONSE_BYTES))

    def _content_length_too_large(self, headers: Any, max_bytes: int) -> bool:
        content_length = headers.get("Content-Length")
        if not content_length:
            return False
        try:
            return int(content_length) > max_bytes
        except ValueError:
            return False

    def _log_safe_text(self, value: Any) -> str:
        return self._clean_text(
            value, max_length=80, preserve_formatting=False
        )

    def _url_allowed(self, url: str) -> bool:
        parsed = urlsplit(url)
        return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS

    def _reply(self, irc, text: str) -> None:
        irc.reply(
            self._clean_text(text, max_length=MAX_REPLY_LENGTH),
            prefixNick=False,
        )

    def _error(self, irc, text: str) -> None:
        irc.error(
            self._clean_text(text, max_length=MAX_REPLY_LENGTH),
            prefixNick=False,
        )

    def _cooldown_remaining(self, irc, msg, channel: Optional[str]) -> int:
        cooldown = self.registryValue("cooldownSeconds", channel)
        if not cooldown:
            return 0

        cooldown = max(0, int(cooldown))
        if cooldown <= 0:
            return 0

        now = time.monotonic()
        key = (
            getattr(irc, "network", ""),
            channel or "PM",
            getattr(msg, "prefix", ""),
        )
        with self._cooldown_lock:
            expired = [
                item
                for item, last_seen in self._cooldowns.items()
                if now - last_seen >= cooldown
            ]
            for item in expired:
                del self._cooldowns[item]

            last_seen = self._cooldowns.get(key)
            if last_seen is None or now - last_seen >= cooldown:
                self._cooldowns[key] = now
                return 0
            return max(1, int(cooldown - (now - last_seen)))

    async def _fetch_url(self, url: str, timeout: int) -> Optional[str]:
        """Fetch data from a URL asynchronously using aiohttp."""
        if not self._url_allowed(url):
            log.error("Blocked UrbanDictionary fetch to unexpected URL.")
            return None

        try:
            headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
            }
            max_bytes = self._max_response_bytes()
            request_timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=request_timeout, headers=headers
                ) as response:
                    if (
                        response.content_length is not None
                        and response.content_length > max_bytes
                    ):
                        log.error(
                            "UrbanDictionary response exceeded the size limit."
                        )
                        return None

                    body = await response.content.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        log.error(
                            "UrbanDictionary response exceeded the size limit."
                        )
                        return None

                    if response.status == 200:
                        return body.decode("utf-8", errors="replace")
                    else:
                        log.error(
                            "UrbanDictionary API fetch failed: HTTP %s, body=%r",
                            response.status,
                            body[:120],
                        )
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            log.error(
                "UrbanDictionary API fetch failed: %s",
                e.__class__.__name__,
            )
            return None

    def _fetch_url_fallback(self, url: str, timeout: int) -> Optional[str]:
        """Fallback fetch path using stdlib urllib when aiohttp fails."""
        if not self._url_allowed(url):
            log.error(
                "Blocked UrbanDictionary fallback fetch to unexpected URL."
            )
            return None

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)
        retry_timeout = max(timeout + 10, timeout * 2)
        max_bytes = self._max_response_bytes()
        for current_timeout in (timeout, retry_timeout):
            try:
                with urllib.request.urlopen(
                    req,
                    timeout=current_timeout,  # nosec B310
                ) as response:
                    if self._content_length_too_large(
                        response.headers, max_bytes
                    ):
                        log.error(
                            "UrbanDictionary fallback response exceeded the size limit."
                        )
                        return None
                    body = response.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        log.error(
                            "UrbanDictionary fallback response exceeded the size limit."
                        )
                        return None
                    return body.decode("utf-8", errors="replace")
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                log.error(
                    "UrbanDictionary fallback fetch failed (timeout=%ss): %s",
                    current_timeout,
                    e.__class__.__name__,
                )
        return None

    def _fetch_define_page_fallback(
        self, term: str, timeout: int
    ) -> Optional[Dict[str, Any]]:
        """Fallback to scraping the Urban Dictionary define page when API fetches fail."""
        url = f"https://www.urbandictionary.com/define.php?term={quote_plus(term)}"
        if not self._url_allowed(url):
            log.error(
                "Blocked UrbanDictionary define-page fetch to unexpected URL."
            )
            return None

        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html"}
        req = urllib.request.Request(url, headers=headers)
        retry_timeout = max(timeout + 10, timeout * 2)
        page_html = None
        max_bytes = self._max_response_bytes()
        for current_timeout in (timeout, retry_timeout):
            try:
                with urllib.request.urlopen(
                    req,
                    timeout=current_timeout,  # nosec B310
                ) as response:
                    if self._content_length_too_large(
                        response.headers, max_bytes
                    ):
                        log.error(
                            "UrbanDictionary define-page response exceeded the size limit."
                        )
                        return None
                    body = response.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        log.error(
                            "UrbanDictionary define-page response exceeded the size limit."
                        )
                        return None
                    page_html = body.decode("utf-8", errors="replace")
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                log.error(
                    "UrbanDictionary define-page fallback failed for %s (timeout=%ss): %s",
                    self._log_safe_text(term),
                    current_timeout,
                    e.__class__.__name__,
                )

        if not page_html:
            return None

        # Try the most descriptive metadata first, then title as a last resort.
        description_patterns = (
            r'property="og:description" content="([^"]+)"',
            r'name="description" content="([^"]+)"',
        )
        description = ""
        for pattern in description_patterns:
            match = re.search(pattern, page_html, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                break

        if not description:
            title_match = re.search(
                r"<title[^>]*>(.*?)</title>",
                page_html,
                re.IGNORECASE | re.DOTALL,
            )
            if title_match:
                description = title_match.group(1).strip()

        if not description:
            return None

        description = html.unescape(description)

        return {
            "list": [
                {
                    "definition": description,
                    "example": "",
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                }
            ],
            "tags": [],
        }

    def _run_coro(self, coro):
        """Run a coroutine in an isolated event loop.

        This avoids collisions with any event loop state in the host process.
        """
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    ####################
    # PUBLIC FUNCTIONS #
    ####################

    def urbandictionary(
        self, irc, msg, args, optlist: List[Tuple[str, Any]], optterm: str
    ):
        """[--disableexamples | --showvotes | --num # | --showtags] <term>

        Fetches definition for <term> on UrbanDictionary.com.

        Use --disableexamples to omit examples.
        Use --showvotes to display vote counts (default: off).
        Use --num # to limit the number of definitions (default: 10).
        Use --showtags to display tags (if available).
        """
        args = {
            "showExamples": True,
            "numberOfDefinitions": self._clamp_count(
                self.registryValue("maxNumberOfDefinitions")
            ),
            "showVotes": False,
            "showTags": False,
        }

        channel = getattr(msg, "channel", None)
        if channel and not self.registryValue("enabled", channel):
            return

        is_valid, optterm, error = self._validate_term(optterm)
        if not is_valid:
            self._error(irc, error)
            return

        cooldown = self._cooldown_remaining(irc, msg, channel)
        if cooldown:
            self._error(
                irc,
                f"Please wait {cooldown}s before using UrbanDictionary again.",
            )
            return

        # Parse options
        for key, value in optlist:
            if key == "disableexamples":
                args["showExamples"] = False
            elif key == "showvotes":
                args["showVotes"] = True
            elif key == "num":
                args["numberOfDefinitions"] = self._clamp_count(value)
            elif key == "showtags":
                args["showTags"] = True

        query = urlencode({"term": optterm})
        url = f"https://api.urbandictionary.com/v0/define?{query}"
        timeout = self._clamp_timeout(self.registryValue("requestTimeout"))

        prefer_define_page = self.registryValue("preferDefinePage")
        json_data = None
        data = None

        if prefer_define_page:
            data = self._fetch_define_page_fallback(optterm, timeout)
            if data is None:
                json_data = self._run_coro(self._fetch_url(url, timeout))
                if not json_data:
                    json_data = self._fetch_url_fallback(url, timeout)
        else:
            json_data = self._run_coro(self._fetch_url(url, timeout))
            if not json_data:
                json_data = self._fetch_url_fallback(url, timeout)
            if not json_data:
                data = self._fetch_define_page_fallback(optterm, timeout)

        if not json_data and not data:
            self._error(irc, f"Could not retrieve data for '{optterm}'.")
            return

        if data is None:
            if json_data is None:
                self._error(irc, f"Could not retrieve data for '{optterm}'.")
                return
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                log.error(
                    "Error parsing Urban Dictionary JSON: %s",
                    e.__class__.__name__,
                )
                self._error(irc, "Failed to parse Urban Dictionary data.")
                return

        definitions = data.get("list", [])

        if not definitions:
            self._error(irc, f"No definition found for '{optterm}'.")
            return

        # Apply slicing limit
        limit = self._clamp_count(args.get("numberOfDefinitions", 10))
        definitions = definitions[:limit]

        MAX_TOTAL_LENGTH = 1000  # Limit total response length in characters
        output = []
        total_length = 0
        include_first = True

        for entry in definitions:
            definition = self._clean_text(
                entry.get("definition", ""), max_length=MAX_ENTRY_LENGTH
            )
            example = self._clean_text(
                entry.get("example", ""), max_length=MAX_ENTRY_LENGTH
            )
            thumbs_up = entry.get("thumbs_up", 0)
            thumbs_down = entry.get("thumbs_down", 0)

            formatted = definition
            if args["showExamples"] and example:
                formatted += f" Example: {example}"
            if args["showVotes"]:
                formatted += f" (+{thumbs_up}/-{thumbs_down})"

            # Ensure at least one definition is included
            if include_first:
                include_first = False
            elif total_length + len(formatted) > MAX_TOTAL_LENGTH:
                break

            output.append(formatted)
            total_length += len(formatted)

        response = " | ".join(output)

        if args["showTags"]:
            tags = data.get("tags", [])
            if tags:
                safe_tags = [
                    self._clean_text(tag, max_length=MAX_TAG_LENGTH)
                    for tag in tags
                ]
                tag_text = " | ".join(tag for tag in safe_tags if tag)
                response = f"{response} | Tags: {tag_text}"

        # Check if ANSI should be disabled
        if self.registryValue("disableANSI"):
            response = ircutils.stripFormatting(response)
            optterm = ircutils.stripFormatting(optterm)

        self._reply(
            irc, self._format_text(optterm, color="red") + " :: " + response
        )

    urbandictionary = wrap(
        urbandictionary,
        [
            getopts(
                {
                    "disableexamples": "",
                    "showvotes": "",
                    "num": ("int"),
                    "showtags": "",
                }
            ),
            ("text"),
        ],
    )


Class = UrbanDictionary

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
