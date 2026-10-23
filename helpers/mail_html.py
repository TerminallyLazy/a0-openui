"""Static email HTML shared by rich previews and reviewed SMTP messages."""
import html
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

LIMIT = 131072
TAGS = set('a abbr b blockquote br caption center code col colgroup dd del div dl dt em h1 h2 h3 h4 h5 h6 hr i img li ol p pre s small span strong sub sup table tbody td th thead tr u ul'.split())
ATTRS = set('alt title width height align valign bgcolor border cellpadding cellspacing colspan rowspan role dir lang'.split())
CSS = set('color background-color font font-family font-size font-style font-weight line-height letter-spacing text-align text-decoration text-transform vertical-align white-space word-break overflow-wrap display width min-width max-width height min-height max-height margin margin-top margin-right margin-bottom margin-left padding padding-top padding-right padding-bottom padding-left border border-top border-right border-bottom border-left border-color border-width border-style border-radius border-collapse border-spacing table-layout'.split())


def safe_url(value, image=False):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        return ''
    try:
        url = urlsplit(value)
        if url.scheme.lower() in {'https', 'http'} and url.hostname and not url.username and not url.password:
            return value
        if not image and url.scheme.lower() == 'mailto' and '@' in url.path and not url.query:
            return value
    except ValueError:
        pass
    return ''


def style(value):
    declarations = []
    for item in str(value).split(';'):
        key, _, val = item.partition(':')
        key, val = key.strip().lower(), val.strip()
        # Deliberately no CSS URLs, escapes, comments, functions or positioning.
        if key in CSS and len(val) <= 250 and re.fullmatch(r"[\w\s#.,%+'\"/!\-]+", val, re.ASCII):
            declarations.append(f'{key}:{val}')
    return ';'.join(declarations)


def sanitize(value):
    if not isinstance(value, str) or len(value.encode('utf-8')) > LIMIT:
        raise ValueError('Rich email must fit within 128 KiB.')
    soup = BeautifulSoup(value, 'html.parser')
    for tag in list(soup.find_all(['script', 'style', 'iframe', 'object', 'embed', 'svg', 'math', 'form', 'input', 'button', 'textarea', 'select', 'meta', 'link', 'base', 'head'])):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in list(soup.find_all(True)):
        if tag.name not in TAGS:
            tag.unwrap()
            continue
        kept = {}
        for key, val in tag.attrs.items():
            if key in ATTRS and isinstance(val, str) and len(val) <= 500:
                kept[key] = val
            elif key == 'style':
                kept[key] = style(val)
            elif (key == 'href' and tag.name == 'a') or (key == 'src' and tag.name == 'img'):
                safe = safe_url(val, image=tag.name == 'img')
                if safe:
                    kept[key] = safe
        if tag.name == 'a':
            kept.update(target='_blank', rel='noopener noreferrer')
        tag.attrs = kept
    body = str(soup)
    if len(body.encode('utf-8')) > LIMIT:
        raise ValueError('Rich email must fit within 128 KiB after formatting.')
    return '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;font-family:Arial,sans-serif;color:#18212f;background-color:#ffffff">' + body + '</body></html>'


def plain(value):
    soup = BeautifulSoup(value, 'html.parser')
    for link in soup.find_all('a', href=True):
        link.append(' (' + link['href'] + ')')
    return soup.get_text('\n', strip=True)


def from_message(msg, fallback):
    part = msg.get_body(preferencelist=('html',))
    content = part.get_content() if part else None
    if not isinstance(content, str) or len(content.encode('utf-8')) > LIMIT:
        return sanitize('<pre style="white-space:pre-wrap">' + html.escape(fallback) + '</pre>')
    return sanitize(content)
