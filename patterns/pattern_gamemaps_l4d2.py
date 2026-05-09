from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as http_requests
except Exception:  # pragma: no cover - fallback only when curl_cffi is unavailable
    import requests as http_requests

BASE_SITE = "https://www.gamemaps.com"
LISTING_PATH = "/l4d2/files"
DOWNLOAD_ENDPOINT = "/downloads/download"
MAX_ITEMS = 5
LISTING_SCAN_LIMIT = 40
REQUEST_TIMEOUT = 30

DISALLOWED_SCRIPT_PATTERN = re.compile(
    r"["
    r"\u0400-\u052f"  # Cyrillic
    r"\u2de0-\u2dff"
    r"\ua640-\ua69f"
    r"\u0370-\u03ff"  # Greek
    r"\u1f00-\u1fff"
    r"\u0590-\u05ff"  # Hebrew
    r"\u0600-\u06ff"  # Arabic
    r"\u0750-\u077f"
    r"\u08a0-\u08ff"
    r"\u0900-\u097f"  # Indic scripts (Devanagari family)
    r"\u0980-\u09ff"
    r"\u0a00-\u0a7f"
    r"\u0a80-\u0aff"
    r"\u0b00-\u0b7f"
    r"\u0b80-\u0bff"
    r"\u0c00-\u0c7f"
    r"\u0c80-\u0cff"
    r"\u0d00-\u0d7f"
    r"\u0d80-\u0dff"
    r"\u0e00-\u0e7f"  # Thai
    r"\u0e80-\u0eff"  # Lao
    r"\u0f00-\u0fff"  # Tibetan
    r"\u1000-\u109f"  # Myanmar
    r"\u1780-\u17ff"  # Khmer
    r"\u1800-\u18af"  # Mongolian
    r"\u1100-\u11ff"  # Hangul Jamo
    r"\u3130-\u318f"
    r"\uac00-\ud7af"  # Hangul syllables
    r"\u3040-\u30ff"  # Hiragana/Katakana
    r"\u31f0-\u31ff"
    r"\u2e80-\u2eff"  # CJK radicals
    r"\u3000-\u303f"  # CJK punctuation
    r"\u3400-\u4dbf"  # CJK ext A
    r"\u4e00-\u9fff"  # CJK unified ideographs
    r"\uf900-\ufaff"  # CJK compatibility
    r"\uff00-\uffef"  # Full-width forms
    r"]"
)

AD_LINE_PATTERNS = [
    re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}\b", re.IGNORECASE),
    re.compile(r"^\*?\s*server\d*\s*:", re.IGNORECASE),
    re.compile(r"^\*?\s*hostname\s*:", re.IGNORECASE),
    re.compile(r"\bdiscord(?:\.gg|\.com/invite)\b", re.IGNORECASE),
    re.compile(r"\bjoin\s+(?:our\s+)?(?:discord|server)\b", re.IGNORECASE),
    re.compile(r"\bplay\s+on\s+(?:our\s+)?server\b", re.IGNORECASE),
    re.compile(r"^\s*a server\b.*for gameplay:?\s*$", re.IGNORECASE),
    re.compile(r"\bpatreon\b|\bdonate\b|\bsponsor(?:ed)?\b|\bpromo(?:code)?\b", re.IGNORECASE),
    re.compile(r"\bnot authorized for redistribution\b|\bnot authorized for posting on steam\b", re.IGNORECASE),
    re.compile(r"\bcopyright\b.*\b\d{4}\b", re.IGNORECASE),
    re.compile(r"^\s*disclosure\s*$", re.IGNORECASE),
]

LIST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ro;q=0.8",
    "Referer": BASE_SITE + "/",
}


def create_session():
    try:
        return http_requests.Session(impersonate="chrome")
    except TypeError:
        return http_requests.Session()


def normalize_whitespace(value):
    return re.sub(r"\s+", " ", value or "").strip()


def absolute_url(url):
    return urljoin(BASE_SITE, url or "")


def unique_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def has_only_standard_scripts(value):
    text = normalize_whitespace(value)
    if not text:
        return False
    return not DISALLOWED_SCRIPT_PATTERN.search(text)


def has_only_standard_scripts_article(title, teaser, description_text):
    sample = " ".join(part for part in [title, teaser, description_text] if part)
    return has_only_standard_scripts(sample)


def strip_description_ads(raw_text):
    if not raw_text:
        return ""

    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    kept = []

    for line in lines:
        stripped = normalize_whitespace(line)
        if not stripped:
            if kept and kept[-1] != "":
                kept.append("")
            continue

        if any(pattern.search(stripped) for pattern in AD_LINE_PATTERNS):
            continue

        kept.append(stripped)

    # Trim extra leading/trailing blank lines.
    while kept and kept[0] == "":
        kept.pop(0)
    while kept and kept[-1] == "":
        kept.pop()

    return "\n".join(kept)


def to_rfc2822(pub_date_iso):
    if not pub_date_iso:
        return ""

    value = pub_date_iso.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return format_datetime(dt.astimezone(timezone.utc))


def collect_listing_entries(list_soup):
    section = list_soup.select_one("section.files")
    if not section:
        return []

    items = []
    for index, article in enumerate(section.select("article.list-item.list-item-file"), start=1):
        if index > LISTING_SCAN_LIMIT:
            break

        anchor = article.select_one("header a[href]") or article.select_one("a[href]")
        if not anchor:
            continue

        details_url = absolute_url(anchor.get("href", ""))
        if not details_url:
            continue

        title_el = article.select_one(".title")
        teaser_el = article.select_one("p")
        time_el = article.select_one("time[datetime]")

        title = normalize_whitespace(title_el.get_text(" ", strip=True) if title_el else "")
        teaser = normalize_whitespace(teaser_el.get_text("\n", strip=True) if teaser_el else "")
        pub_date = to_rfc2822(time_el.get("datetime", "") if time_el else "")

        if not has_only_standard_scripts(f"{title} {teaser}"):
            continue

        items.append(
            {
                "title": title or "No title",
                "details_url": details_url,
                "teaser": teaser,
                "pubDate": pub_date,
            }
        )

        if len(items) >= MAX_ITEMS * 4:
            break

    return items


def extract_title(detail_soup, fallback_title):
    title_row = detail_soup.select_one("div.title-row")
    if not title_row:
        return fallback_title

    clone = BeautifulSoup(str(title_row), "html.parser")
    row = clone.select_one("div.title-row")
    if not row:
        return fallback_title

    type_label_el = row.select_one("aside.item-typelabel")
    type_label = normalize_whitespace(type_label_el.get_text(" ", strip=True) if type_label_el else "")
    if type_label_el:
        type_label_el.decompose()

    title_text = normalize_whitespace(row.get_text(" ", strip=True))
    if not title_text:
        title_text = fallback_title

    if type_label:
        return f"[ {type_label} ] {title_text}"
    return title_text


def extract_description_html(detail_soup, fallback_text):
    desc_section = detail_soup.select_one("section.desc.expandable")
    if not desc_section:
        text = fallback_text or "Description is not available."
        return f'<div class="gm-description-text">{escape(text)}</div>', [], text

    pre_block = desc_section.select_one("pre")
    if not pre_block:
        text = normalize_whitespace(desc_section.get_text(" ", strip=True))
        text = text or fallback_text or "Description is not available."
        return f'<div class="gm-description-text">{escape(text)}</div>', [], text

    clone = BeautifulSoup(str(pre_block), "html.parser")
    pre_node = clone.select_one("pre")
    if not pre_node:
        text = fallback_text or "Description is not available."
        return f'<div class="gm-description-text">{escape(text)}</div>', [], text

    for expand in pre_node.select("span.expand"):
        expand.unwrap()

    workshop_links = []
    for anchor in pre_node.select("a[href]"):
        href = absolute_url(anchor.get("href", ""))
        if not href:
            continue

        if "steamcommunity.com" in href.lower():
            workshop_links.append(href)

    description_plain_text = strip_description_ads(pre_node.get_text("\n", strip=False))
    if not description_plain_text.strip():
        description_plain_text = normalize_whitespace(fallback_text or "Description is not available.")

    description_html = f'<div class="gm-description-text">{escape(description_plain_text)}</div>'
    return description_html, unique_preserve_order(workshop_links), description_plain_text


def extract_download_link(session, detail_soup, details_url):
    form = detail_soup.select_one(f'form[action="{DOWNLOAD_ENDPOINT}"]')
    if not form:
        form = detail_soup.select_one('form[action="/downloads/download"]')
    if not form:
        return ""

    file_id_input = form.select_one('input[name="ids[]"]')
    file_id = file_id_input.get("value", "").strip() if file_id_input else ""
    if not file_id:
        return ""

    payload = {
        "ids[]": file_id,
        "noqueue": "true",
        "direct": "true",
    }
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,ro;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE_SITE,
        "Referer": details_url,
    }

    try:
        response = session.post(
            absolute_url(DOWNLOAD_ENDPOINT),
            headers=headers,
            data=payload,
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT,
        )
    except Exception:
        return ""

    location = response.headers.get("location", "")
    if location:
        return absolute_url(location)

    response_url = getattr(response, "url", "")
    if response_url and "downloads/download" not in response_url:
        return response_url

    return ""


def extract_media_urls(detail_soup):
    candidates = []

    selectors = [
        "div.media section.media-carousel article.carousel-item-image img[src]",
        "div.media section.media-carousel .items img[src]",
        "div.media section.extra-media .media-tile img[src]",
    ]
    for selector in selectors:
        for image in detail_soup.select(selector):
            src = absolute_url(image.get("src", ""))
            if not src:
                continue
            if "logo.svg" in src:
                continue
            candidates.append(src)

    return unique_preserve_order(candidates)[:8]


def build_gallery_id(details_url):
    match = re.search(r"/details/(\d+)", details_url)
    if match:
        return f"gm-gallery-{match.group(1)}"
    return "gm-gallery-default"


def build_action_buttons(download_url, workshop_links):
    buttons = []

    if download_url:
        href = escape(download_url, quote=True)
        buttons.append(
            f'<a class="gm-btn gm-btn-download" href="{href}" target="_blank" rel="nofollow noopener noreferrer">Direct Download</a>'
        )

    for index, link in enumerate(workshop_links[:2], start=1):
        label = "Steam Workshop" if index == 1 else f"Steam Workshop {index}"
        href = escape(link, quote=True)
        buttons.append(
            f'<a class="gm-btn gm-btn-steam" href="{href}" target="_blank" rel="nofollow noopener noreferrer">{label}</a>'
        )

    if not buttons:
        return ""

    return f'<div class="gm-actions">{"".join(buttons)}</div>'


def build_media_block(media_urls, gallery_id):
    if not media_urls:
        return ""

    items = []
    for index, media_url in enumerate(media_urls, start=1):
        href = escape(media_url, quote=True)
        items.append(
            """
            <a class="spoilerGalleryItem"
               href="{href}"
               data-gm-gallery="{gallery_id}"
               data-gm-index="{index_zero}"
               data-ipslightbox
               data-ipslightbox-group="{gallery_id}"
               target="_blank"
               rel="noopener noreferrer">
                <img src="{href}" alt="GameMaps media {index}" loading="lazy">
            </a>
            """.format(href=href, index=index, index_zero=index - 1, gallery_id=gallery_id)
        )

    return f"""
    <div class="gm-media-label">Media</div>
    <div class="ipsSpoiler cleanSpoilerGallery" data-ipsspoiler>
        <div class="ipsSpoiler_header">
            <span>Media gallery</span>
        </div>
        <div class="ipsSpoiler_contents ipsClearfix">
            <div class="spoilerGalleryGrid">
                {''.join(items)}
            </div>
        </div>
    </div>

    <div class="gmLightbox" data-gm-lightbox="{gallery_id}" hidden>
        <button type="button" class="gmLightboxBtn gmLightboxClose" aria-label="Close">&times;</button>
        <button type="button" class="gmLightboxBtn gmLightboxPrev" aria-label="Previous image">&#10094;</button>
        <img class="gmLightboxImage" src="" alt="">
        <button type="button" class="gmLightboxBtn gmLightboxNext" aria-label="Next image">&#10095;</button>
        <div class="gmLightboxCounter">1 / {len(media_urls)}</div>
    </div>

    {build_gallery_script()}
    """


def build_gallery_script():
    return """
    <script>
    (function () {
        if (window.__gmGalleryInitialized) {
            return;
        }
        window.__gmGalleryInitialized = true;

        function getOpenModal() {
            return document.querySelector('.gmLightbox.is-open');
        }

        function getGalleryLinks(group) {
            var allLinks = Array.prototype.slice.call(document.querySelectorAll('a[data-gm-gallery]'));
            return allLinks.filter(function (link) {
                return link.getAttribute('data-gm-gallery') === group;
            });
        }

        function closeModal(modal) {
            if (!modal) {
                return;
            }
            modal.classList.remove('is-open');
            modal.setAttribute('hidden', 'hidden');
            var image = modal.querySelector('.gmLightboxImage');
            if (image) {
                image.removeAttribute('src');
            }
            document.documentElement.classList.remove('gmLightboxOpen');
        }

        function renderModal(modal) {
            var links = modal.__gmLinks || [];
            if (!links.length) {
                return;
            }

            var index = modal.__gmIndex || 0;
            if (index < 0) {
                index = links.length - 1;
            }
            if (index >= links.length) {
                index = 0;
            }

            modal.__gmIndex = index;
            var activeLink = links[index];
            var image = modal.querySelector('.gmLightboxImage');
            var thumb = activeLink.querySelector('img');
            var counter = modal.querySelector('.gmLightboxCounter');

            if (image) {
                image.setAttribute('src', activeLink.getAttribute('href'));
                image.setAttribute('alt', thumb ? (thumb.getAttribute('alt') || '') : '');
            }

            if (counter) {
                counter.textContent = (index + 1) + ' / ' + links.length;
            }
        }

        function openModal(modal, links, startIndex) {
            if (!modal || !links.length) {
                return;
            }
            modal.__gmLinks = links;
            modal.__gmIndex = startIndex;
            renderModal(modal);
            modal.removeAttribute('hidden');
            modal.classList.add('is-open');
            document.documentElement.classList.add('gmLightboxOpen');
        }

        function stepModal(modal, delta) {
            if (!modal) {
                return;
            }
            modal.__gmIndex = (modal.__gmIndex || 0) + delta;
            renderModal(modal);
        }

        document.addEventListener('click', function (event) {
            var galleryItem = event.target.closest('a[data-gm-gallery]');
            if (galleryItem) {
                var group = galleryItem.getAttribute('data-gm-gallery');
                var modal = document.querySelector('.gmLightbox[data-gm-lightbox="' + group + '"]');
                var links = getGalleryLinks(group);
                var startIndex = parseInt(galleryItem.getAttribute('data-gm-index') || '0', 10);
                if (modal && links.length) {
                    event.preventDefault();
                    openModal(modal, links, startIndex);
                }
                return;
            }

            var closeButton = event.target.closest('.gmLightboxClose');
            if (closeButton) {
                closeModal(closeButton.closest('.gmLightbox'));
                return;
            }

            var prevButton = event.target.closest('.gmLightboxPrev');
            if (prevButton) {
                stepModal(prevButton.closest('.gmLightbox'), -1);
                return;
            }

            var nextButton = event.target.closest('.gmLightboxNext');
            if (nextButton) {
                stepModal(nextButton.closest('.gmLightbox'), 1);
                return;
            }

            var openModalElement = event.target.classList.contains('gmLightbox') ? event.target : null;
            if (openModalElement) {
                closeModal(openModalElement);
            }
        });

        document.addEventListener('keydown', function (event) {
            var modal = getOpenModal();
            if (!modal) {
                return;
            }

            if (event.key === 'Escape') {
                closeModal(modal);
            } else if (event.key === 'ArrowLeft') {
                stepModal(modal, -1);
            } else if (event.key === 'ArrowRight') {
                stepModal(modal, 1);
            }
        });
    })();
    </script>
    """


def set_style():
    return """
    <style>
        .gmLightboxOpen {
            overflow: hidden;
        }

        .gm-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin: 0 0 12px 0;
        }

        .gm-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 38px;
            padding: 8px 14px;
            border-radius: 8px;
            text-decoration: none;
            color: #ffffff;
            font-weight: 600;
            font-size: 14px;
        }

        .gm-btn-download {
            background: #1d9f61;
        }

        .gm-btn-steam {
            background: #1d5fb5;
        }

        .gm-media-label {
            margin: 6px 0 8px 0;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: .2px;
        }

        .cleanSpoilerGallery {
            margin: 14px 0;
            border-radius: 10px;
            overflow: hidden;
        }

        .cleanSpoilerGallery .ipsSpoiler_header {
            padding: 11px 14px;
            background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.03));
            border: 1px solid rgba(255,255,255,.08);
            border-bottom: 0;
            border-radius: 10px 10px 0 0;
        }

        .cleanSpoilerGallery .ipsSpoiler_header span {
            font-size: 13px;
            font-weight: 600;
            letter-spacing: .2px;
            color: #e8e8e8;
        }

        .cleanSpoilerGallery .ipsSpoiler_contents {
            padding: 12px;
            background: rgba(255,255,255,.035);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 0 0 10px 10px;
        }

        .cleanSpoilerGallery .spoilerGalleryGrid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: flex-start;
        }

        .cleanSpoilerGallery .spoilerGalleryItem {
            display: inline-block;
            overflow: hidden;
            border-radius: 8px;
            background: #111;
            border: 1px solid rgba(255,255,255,.07);
            width: 188px;
            text-decoration: none;
        }

        .cleanSpoilerGallery .spoilerGalleryItem img {
            width: 100%;
            height: 112px;
            object-fit: cover;
            display: block;
            border-radius: 8px;
            transition: transform .25s ease, filter .25s ease;
        }

        .cleanSpoilerGallery .spoilerGalleryItem:hover img {
            transform: scale(1.025);
            filter: brightness(1.06);
        }

        .gm-description-text {
            white-space: pre-wrap;
            line-height: 1.6;
            font-size: 15px;
        }

        .gm-description-text a {
            color: #1d5fb5;
            text-decoration: underline;
        }

        .gm-description-text a.gm-inline-steam {
            display: inline-block;
            margin-top: 6px;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid #1d5fb5;
            text-decoration: none;
        }

        .gmLightbox {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, .86);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2147483640;
            padding: 20px;
        }

        .gmLightbox.is-open {
            display: flex;
        }

        .gmLightboxImage {
            max-width: min(92vw, 1500px);
            max-height: 84vh;
            border-radius: 8px;
            object-fit: contain;
            box-shadow: 0 12px 36px rgba(0, 0, 0, .5);
        }

        .gmLightboxBtn {
            position: fixed;
            border: 0;
            background: rgba(22, 22, 22, .75);
            color: #fff;
            cursor: pointer;
            border-radius: 8px;
            font-size: 22px;
            line-height: 1;
            padding: 10px 12px;
        }

        .gmLightboxClose {
            top: 16px;
            right: 16px;
            font-size: 28px;
            padding: 8px 12px;
        }

        .gmLightboxPrev {
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
        }

        .gmLightboxNext {
            right: 16px;
            top: 50%;
            transform: translateY(-50%);
        }

        .gmLightboxCounter {
            position: fixed;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%);
            color: #fff;
            background: rgba(18, 18, 18, .72);
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 12px;
        }

        @media (max-width: 640px) {
            .cleanSpoilerGallery .spoilerGalleryItem {
                width: calc(50% - 5px);
            }

            .cleanSpoilerGallery .spoilerGalleryItem img {
                height: 105px;
            }

            .gm-btn {
                width: 100%;
            }

            .gmLightboxPrev,
            .gmLightboxNext {
                font-size: 18px;
                padding: 8px 10px;
            }
        }

        @media (max-width: 420px) {
            .cleanSpoilerGallery .spoilerGalleryItem {
                width: 100%;
            }

            .cleanSpoilerGallery .spoilerGalleryItem img {
                height: 150px;
            }
        }
    </style>
    """


def build_description_payload(description_html, download_url, workshop_links, media_urls, gallery_id):
    actions_html = build_action_buttons(download_url, workshop_links)
    media_html = build_media_block(media_urls, gallery_id)

    return f"""
    {set_style()}
    {actions_html}
    {media_html}
    {description_html}
    """


def fetch_article_data(session, listing_entry, list_url):
    details_url = listing_entry["details_url"]

    detail_headers = dict(LIST_HEADERS)
    detail_headers["Referer"] = list_url

    try:
        response = session.get(details_url, headers=detail_headers, timeout=REQUEST_TIMEOUT)
    except Exception:
        return None

    if response.status_code != 200:
        return None

    detail_soup = BeautifulSoup(response.text, "html.parser")

    title = extract_title(detail_soup, listing_entry["title"])
    description_html, workshop_links, description_plain_text = extract_description_html(detail_soup, listing_entry["teaser"])

    if not has_only_standard_scripts_article(title, listing_entry["teaser"], description_plain_text):
        return None

    download_url = extract_download_link(session, detail_soup, details_url)
    media_urls = extract_media_urls(detail_soup)
    gallery_id = build_gallery_id(details_url)

    full_description = build_description_payload(
        description_html=description_html,
        download_url=download_url,
        workshop_links=workshop_links,
        media_urls=media_urls,
        gallery_id=gallery_id,
    )

    return {
        "title": title,
        "link": details_url,
        "description": full_description,
        "pubDate": listing_entry["pubDate"],
    }


def scrape_gamemaps_files(url):
    session = create_session()
    try:
        response = session.get(url, headers=LIST_HEADERS, timeout=REQUEST_TIMEOUT)
    except Exception:
        session.close()
        return []

    if response.status_code != 200:
        session.close()
        return []

    list_soup = BeautifulSoup(response.text, "html.parser")
    listing_entries = collect_listing_entries(list_soup)

    articles = []
    for listing_entry in listing_entries:
        if len(articles) >= MAX_ITEMS:
            break

        article_data = fetch_article_data(session, listing_entry, url)
        if article_data:
            articles.append(article_data)

    session.close()
    return articles


def fetch_data(url):
    return scrape_gamemaps_files(url or absolute_url(LISTING_PATH))
