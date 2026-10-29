"""Deterministic helpers; measurements do not establish human identity.

SPDX-License-Identifier: Apache-2.0
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import re
from urllib.parse import urlsplit

UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
X_EPOCH_MS = 1288834974657


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def utc(value):
    """Require an explicit offset; never assume a timezone for a naive time."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("An explicit UTC offset is required")
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def snowflake_utc(identifier):
    """Decode a modern X Snowflake *claim*, not authenticate the supplied ID."""
    if not isinstance(identifier, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", identifier):
        raise ValueError("Use an exact positive decimal ID string")
    n = int(identifier)
    if n >= 2**63:
        raise ValueError("ID exceeds signed 64-bit Snowflake range")
    timestamp = EPOCH + timedelta(milliseconds=(n >> 22) + X_EPOCH_MS)
    return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timestamp_delta_seconds(identifier, observed):
    a = datetime.fromisoformat(snowflake_utc(identifier).replace("Z", "+00:00"))
    b = datetime.fromisoformat(utc(observed).replace("Z", "+00:00"))
    return (b - a).total_seconds()


def receipt(path, url, retrieved_at, access_basis, locator):
    """Hash a locally acquired public-source capture; no network is performed.

    The access declaration is supplied by the researcher, not independently
    authenticated. A content hash proves byte identity, not source truth.
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTPS source URL without credentials is required")
    if access_basis != "public_without_login":
        raise ValueError("This prototype accepts public-without-login captures only")
    if not locator.strip():
        raise ValueError("Provide a page, JSON path, post ID, or other locator")
    raw = path.read_bytes()
    return {"url": url, "retrieved_at_utc": utc(retrieved_at),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "access_basis": access_basis, "locator": locator,
            "access_verification": "researcher_attested", "filename": path.name}


def summarize_posts(posts):
    """Descriptive features only. Explicit author/quote/RT/thread fields required."""
    from statistics import median
    seen, groups, exclusions = set(), {}, {}
    for p in posts:
        if any(not isinstance(p[k], str) or not p[k] for k in ("platform", "post_id", "account_id")):
            raise ValueError("Platform and account/post IDs must be nonempty strings")
        key = (p["platform"], p["post_id"])
        if key in seen:
            raise ValueError("Duplicate post ID; resolve before comparison")
        seen.add(key)
        for field in ("is_target", "is_retweet", "is_quote", "is_partial"):
            if type(p[field]) is not bool:
                raise ValueError(f"{field} must be boolean")
        reason = next((f for f in ("is_retweet", "is_quote", "is_partial") if p[f]), None)
        if not p["is_target"]:
            reason = "context_author"
        text = re.sub(r"https?://\S+|@[A-Za-z0-9_]+", "", p["text"])
        words = re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", text)
        if not words:
            reason = reason or "no_latin_words"
        if reason:
            exclusions[reason] = exclusions.get(reason, 0) + 1
            continue
        group = groups.setdefault((p["platform"], p["account_id"]), [])
        group.append((p, words, re.search(r"[A-Za-z]", text).group().islower()))
    summaries = []
    for (platform, account), rows in sorted(groups.items()):
        standalone = [r for r in rows if not r[0]["thread_id"]]
        summaries.append({"platform": platform, "account_id": account,
                          "posts": len(rows), "tokens": sum(len(r[1]) for r in rows),
                          "median_tokens": median(len(r[1]) for r in rows),
                          "lowercase_initial_count": sum(r[2] for r in rows),
                          "without_threads_posts": len(standalone),
                          "without_threads_tokens": sum(len(r[1]) for r in standalone),
                          "authorship_probability": None})
    return {"groups": summaries, "exclusions": exclusions,
            "scope": "ASCII-Latin descriptive features; no authorship inference"}


def direct_funding(edges, payer, payee):
    """Return only explicit paid-transfer edges for this exact entity pair.

    No path traversal, currency conversion, summing of duplicate disclosures,
    conflation of commitments with payments, or inference of donor direction.
    Entity IDs must already be resolved by a researcher.
    """
    result = []
    for edge in edges:
        if edge["payer"] != payer or edge["payee"] != payee or edge["status"] != "paid":
            continue
        if not edge["source_ids"]:
            raise ValueError("Funding edge has no source")
        amount = Decimal(edge["amount"])
        if not amount.is_finite() or amount < 0:
            raise ValueError("Use a finite nonnegative amount; record refunds separately")
        result.append(edge)
    return {"direct_payment_edges": result,
            "finding": "documented_in_supplied_edges" if result else "not_established_in_supplied_edges",
            "direction_or_coordination_established": False}
