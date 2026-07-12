#!/usr/bin/env python3
"""Validate atomic claims, evidence hashes, audits, and document claim coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from runtime_guard import run_guarded


SCHEMA_VERSION = 1
STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
RISKS = {"normal", "high"}
CLAIM_TYPES = {
    "behavior-trigger", "behavior-step", "behavior-branch", "input", "output",
    "side-effect-call", "endpoint-contract", "field", "validation", "data-read",
    "data-write", "state-transition", "configuration", "dependency", "failure",
    "retry", "mapping", "business-meaning", "business-rule", "business-outcome",
    "coverage-gap", "absence", "other",
}
MACHINE_REQUIRED_TYPES = {
    "behavior-trigger", "behavior-step", "behavior-branch", "input", "output",
    "side-effect-call", "endpoint-contract", "field", "validation", "data-read",
    "data-write", "state-transition", "configuration", "dependency", "failure",
    "retry", "mapping",
}
HIGH_RISK_TYPES = {"state-transition", "retry"}
VERIFICATION_MODES = {"contains-all", "contains-any", "manual"}
FORBIDDEN_EVIDENCE_NAMES = {
    "knowledge-manifest.yaml", "evidence-index.json", "claim-ledger.json", "claim-audit.json",
}
FORBIDDEN_EVIDENCE_PARTS = {"repository-knowledge-pack", ".work"}
GENERIC_RENDER_TERMS = {
    "the", "and", "this", "that", "unknown", "confirmed", "inferred", "conflicting",
    "behavior", "request", "system", "result", "status", "的", "和", "未知", "行为", "请求", "系统", "结果", "状态",
}
SOURCE_KINDS = {
    "implementation", "test", "schema", "configuration", "iac", "comment", "naming",
}
RELATIONS = {"supports", "contradicts", "context"}
SUPPORT_LEVELS = {"direct", "indirect", "context"}
AUDIT_VERDICTS = {"Pass", "Revise", "Reject"}
AUDIT_REVIEW_MODES = {"independent-subagent", "separate-context"}
CLAIM_ID_RE = re.compile(r"^CLM-[A-Za-z0-9][A-Za-z0-9._-]*$")
REFERENCE_RE = re.compile(r"^(?P<path>.+):(?P<start>\d+)(?:-(?P<end>\d+))?$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CLAIM_MARKER_RE = re.compile(
    r"<!--\s*claims:\s*(?P<ids>CLM-[A-Za-z0-9._-]+(?:[\s,]+CLM-[A-Za-z0-9._-]+)*)\s*-->",
    re.I,
)
UNKNOWN_SIGNAL_RE = re.compile(
    r"\b(?:unknown|not established|not observed|cannot determine|unavailable|unresolved)\b|"
    r"未知|无法确定|未观察到|未能确认|不可用|尚未解决|[?？]",
    re.I,
)
HIGH_RISK_RE = re.compile(
    r"\b(?:authentication|authorization|monetary|amount|currency|persist(?:ed|ence)?|commit(?:ted)?|"
    r"transaction(?:al)?|deliver(?:ed|y)?|publish(?:ed)?|retry|dlq|dead.?letter|concurren(?:cy|t)|"
    r"idempoten(?:cy|t)|http\s*[1-5]\d\d|(?:status(?:\s*code)?\s*)[1-5]\d\d|"
    r"reject(?:s|ed|ion)?|consumer-visible\s+failure|business\s+exception|http\s+outcome|"
    r"(?:save|send|publish|update)\w*\s+(?:succeed\w*|complete\w*|success\w*))\b|"
    r"认证|授权|金额|货币|持久化|提交|事务|投递|送达|发布成功|重试|死信|并发|幂等|拒绝|消费者可见失败|业务异常",
    re.I,
)
COMPOUND_SIGNAL_RE = re.compile(r"\b(?:and|as well as)\b|[,;]|以及|并且|而且|和|及|、|，|；", re.I)
MULTI_SENTENCE_RE = re.compile(
    r"(?<!e\.g)(?<!i\.e)(?<=[.!?。！？])\s+(?=[A-Z\u3400-\u9fff])"
)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-+*]|\d+\.)\s+")
FENCE_RE = re.compile(r"^\s*```(?P<language>[A-Za-z0-9_-]*)")
GENERIC_VERIFICATION_TERMS = GENERIC_RENDER_TERMS | {
    "function", "method", "value", "field", "input", "output", "true", "false",
    "none", "null", "call", "return", "data", "record", "函数", "方法", "值", "字段",
    "输入", "输出", "调用", "返回", "数据", "记录",
}
SEMANTIC_EVIDENCE_RULES = (
    (
        re.compile(r"\b(?:encrypt(?:s|ed|ion)?|decrypt(?:s|ed|ion)?|cipher|redact(?:s|ed|ion)?|mask(?:s|ed|ing)?)\b|加密|解密|脱敏|掩码", re.I),
        re.compile(r"\b(?:encrypt|decrypt|cipher|crypto|kms|redact|mask)\w*\b|加密|解密|脱敏|掩码", re.I),
        "encryption/redaction",
    ),
    (
        re.compile(r"\b(?:persist(?:s|ed|ence)?|commit(?:s|ted)?|stored?|database\s+write|durable)\b|持久化|提交事务|写入数据库", re.I),
        re.compile(r"\b(?:persist|commit|save|insert|update|putitem|updateitem|transaction)\w*\b|持久化|提交|保存|写入", re.I),
        "persistence/commit",
    ),
    (
        re.compile(r"\b(?:deliver(?:s|ed|y)?|received\s+by|published\s+successfully)\b|投递成功|已送达|已接收|发布成功", re.I),
        re.compile(r"\b(?:deliver|receipt|ack|publish|send)\w*\b|投递|送达|接收|发布", re.I),
        "delivery/receipt",
    ),
    (
        re.compile(r"\b(?:reject(?:s|ed|ion)?|consumer-visible\s+failure|business\s+exception|http\s+outcome)\b|拒绝|消费者可见失败|业务异常", re.I),
        re.compile(r"\b(?:reject|deny|error|exception|statuscode|http|response)\w*\b|拒绝|错误|异常|状态码|响应", re.I),
        "rejection/consumer outcome",
    ),
    (
        re.compile(r"\b(?:retain(?:s|ed|ention)?|delete(?:s|d|ion)?|purge(?:s|d)?|expire(?:s|d|ation)?)\b|保留|删除|清除|过期", re.I),
        re.compile(r"\b(?:retain|delete|purge|expire|ttl|retention)\w*\b|保留|删除|清除|过期", re.I),
        "retention/deletion",
    ),
    (
        re.compile(r"\b(?:authorize(?:s|d|ation)?|authenticate(?:s|d|ion)?|permission|access\s+control)\b|授权|认证|权限|访问控制", re.I),
        re.compile(r"\b(?:authorize|authenticate|permission|scope|role|jwt|oauth)\w*\b|授权|认证|权限|角色", re.I),
        "authorization/authentication",
    ),
)

# These semantics materially change how a reader understands a Narrative
# document.  Unlike v1 render-term checks, the v2 check is document-level and
# semantic: wording is free, but an affirmative high-risk conclusion still
# needs a compatible passing Claim.
MATERIAL_RULE_CLAIM_TYPES = {
    "encryption/redaction": {"field", "mapping", "validation", "configuration", "data-write"},
    "persistence/commit": {"data-write", "state-transition", "side-effect-call"},
    "delivery/receipt": {"side-effect-call", "output", "failure", "retry", "business-outcome"},
    "rejection/consumer outcome": {"failure", "output", "endpoint-contract", "validation", "business-outcome"},
    "retention/deletion": {"data-write", "state-transition", "configuration"},
    "authorization/authentication": {"validation", "endpoint-contract", "business-rule", "configuration"},
}
MATERIAL_RULES_REQUIRING_HIGH_RISK = {
    "persistence/commit",
    "delivery/receipt",
    "rejection/consumer outcome",
    "authorization/authentication",
    "monetary behavior",
    "transaction/rollback",
    "retry/idempotency/concurrency",
    "completed external outcome",
    "consumer-visible HTTP outcome",
    "business state transition",
}
NARRATIVE_MATERIAL_RULES = tuple(
    (
        semantic_pattern,
        semantic_label,
        MATERIAL_RULE_CLAIM_TYPES[semantic_label],
        semantic_label in MATERIAL_RULES_REQUIRING_HIGH_RISK,
    )
    for semantic_pattern, _evidence_pattern, semantic_label in SEMANTIC_EVIDENCE_RULES
) + (
    (
        re.compile(r"\b(?:amount|money|monetary|currency|fee|balance|payment)\b|金额|货币|费用|余额|支付", re.I),
        "monetary behavior",
        {"field", "mapping", "validation", "data-read", "data-write", "business-rule", "business-outcome"},
        True,
    ),
    (
        re.compile(r"\b(?:transaction(?:al)?|rollback|atomic(?:ity|ally)?)\b|事务|回滚|原子性", re.I),
        "transaction/rollback",
        {"data-write", "state-transition", "configuration", "behavior-step"},
        True,
    ),
    (
        re.compile(r"\b(?:retry|dlq|dead.?letter|idempoten(?:cy|t)|concurren(?:cy|t))\b|重试|死信|幂等|并发", re.I),
        "retry/idempotency/concurrency",
        {"retry", "configuration", "failure", "side-effect-call"},
        True,
    ),
    (
        re.compile(
            r"\b(?:external|downstream|remote)\b[^.!?。！？]{0,50}\b(?:succeed\w*|complete\w*|updated?|accepted?)\b|"
            r"(?:外部|下游|远端)[^。！？]{0,30}(?:成功|完成|已更新|已接受)",
            re.I,
        ),
        "completed external outcome",
        {"side-effect-call", "output", "business-outcome"},
        True,
    ),
    (
        re.compile(r"\b(?:http\s*)?[1-5]\d\d\b|状态码\s*[1-5]\d\d", re.I),
        "consumer-visible HTTP outcome",
        {"endpoint-contract", "failure", "output"},
        True,
    ),
    (
        re.compile(
            r"\b(?:(?:business\s+)?state|status)\b[^.!?。！？|]{0,40}"
            r"\b(?:changes?(?:\s+to)?|transitions?(?:\s+to)?|becomes?|set\s+to)\b|"
            r"\b(?:sets?|changes?|transitions?)\s+(?:the\s+)?(?:(?:business\s+)?state|status)"
            r"(?:\s+from\s+[A-Za-z0-9_.-]+)?\s+to\b|"
            r"(?:业务状态|状态)[^。！？|]{0,20}(?:变更为|转换为|成为|设为)|"
            r"(?:设置|变更|转换)(?:业务状态|状态)为",
            re.I,
        ),
        "business state transition",
        {"state-transition", "data-write", "business-outcome"},
        True,
    ),
    (
        re.compile(r"\b(?:maps?|mapped|mapping|renames?|converts?)\b[^.!?。！？|]{0,60}\b(?:to|into|as)\b|映射|重命名|转换为", re.I),
        "field mapping",
        {"mapping"},
        False,
    ),
    (
        re.compile(r"\b(?:configuration|config(?:uration)?\s+key|environment\s+variable)\b[^.!?。！？|]{0,60}\b(?:controls?|enables?|disables?|changes?|selects?)\b|配置(?:项|键|变量)?[^。！？|]{0,30}(?:控制|启用|禁用|改变|选择)", re.I),
        "configuration effect",
        {"configuration"},
        False,
    ),
    (
        re.compile(
            r"\b(?:(?:defaults?|falls?\s+back)\s+to|(?:has\s+(?:a\s+)?default|default)\s+(?:of|is|=))\b|"
            r"默认(?:为|值)|回退为",
            re.I,
        ),
        "default value",
        {"configuration", "field", "validation", "mapping", "endpoint-contract"},
        False,
    ),
    (
        re.compile(r"\b(?:required|mandatory|must\s+be\s+present|allowed\s+values?|validated?\s+against)\b|必填|必须存在|允许值|校验为", re.I),
        "validation rule",
        {"validation", "field", "endpoint-contract", "business-rule"},
        False,
    ),
    (
        re.compile(r"\b(?:pii|personally\s+identifiable|personal\s+data|sensitive\s+data|confidential)\b|个人信息|个人数据|敏感数据|机密", re.I),
        "sensitivity/PII classification",
        {"field", "mapping", "validation", "configuration"},
        False,
    ),
)

NARRATIVE_ROOT_DOCUMENTS = {
    "knowledge-map.md",
    "tech-pack/repository-overview.md",
    "ba-pack/business-overview.md",
    "ba-pack/behavior-catalog.md",
    "ba-pack/capability-map.md",
    "ba-pack/business-data-lifecycle.md",
    "ba-pack/business-rule-catalog.md",
    "ba-pack/business-exception-catalog.md",
}

# v1 documents were scaffolded with these template-owned headings. Keep them
# structural even after the v2 Narrative templates adopt a reader-first IA.
LEGACY_STRUCTURAL_HEADINGS = {
    "Start here", "Repository at a glance", "Knowledge navigation", "Relationship map",
    "Coverage and known gaps", "Observable responsibility", "Technology and deployment",
    "Entry-point inventory", "Behavior summary", "External connections",
    "Shared rules and components", "Repository-level open questions", "Summary",
    "Trigger and entry point", "API contracts", "BA view", "Behavior flow", "Inputs",
    "External HTTP field mappings", "Related repository knowledge",
    "Preconditions and business rules", "Happy path", "Data access and state changes",
    "Outputs and side effects", "Failures, retries, and partial success",
    "External dependency stubs", "Open questions and conflicts", "Evidence index",
    "BA knowledge navigation", "Business capabilities", "Business actors and participants",
    "Business behavior landscape", "External business participants",
    "Cross-behavior business rules", "Business exceptions and dependencies",
    "Coverage and open questions", "Related BA knowledge", "Business summary",
    "Business trigger and actors", "Business flow", "Business preconditions",
    "Business rules", "Business inputs and outputs", "Business outcomes",
    "Business exceptions", "External business interactions", "Open questions", "Traceability",
}


def _structural_headings() -> set[str]:
    """Load template-owned navigation headings; other headings are factual."""

    headings: set[str] = set()
    assets = Path(__file__).resolve().parent.parent / "assets"
    for template in assets.glob("*template.md"):
        try:
            text = template.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            match = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
            if match:
                headings.add(match.group(1).strip())
    return headings | LEGACY_STRUCTURAL_HEADINGS


STRUCTURAL_HEADINGS = _structural_headings()


def semantic_match_is_qualified(segment: str, match: re.Match[str]) -> bool:
    """Return True only when negation or an explicit Unknown directly qualifies a term."""

    prefix = segment[max(0, match.start() - 60) : match.start()]
    suffix = segment[match.end() : match.end() + 60]
    if re.search(
        r"(?:\bno\b|\bnot\b|\bwithout\b|\bunproven\b|\bunknown\s+whether\b|"
        r"\bcannot\s+determine\s+whether\b|无|未|不|无法确定是否)[^.;|]{0,35}$",
        prefix,
        re.I,
    ):
        return True
    if re.match(
        r"[^.;|]{0,20}\b(?:is|are|remains?)?\s*(?:unknown|unproven|not\s+established|not\s+observed)\b|"
        r"[^。；|]{0,20}(?:未知|未建立|未观察到|无法确定)",
        suffix,
        re.I,
    ):
        return True
    return False


def semantic_match_is_tentative(segment: str, match: re.Match[str]) -> bool:
    """Recognize cautious wording without treating it as an established conclusion."""

    prefix = segment[max(0, match.start() - 70) : match.start()]
    return bool(
        re.search(
            r"(?:\bmay\b|\bmight\b|\bcould\b|\bpossibly\b|\bpotentially\b|"
            r"\bappears?\s+to\b|\bseems?\s+to\b|\blikely\s+to\b|可能|也许|或许|似乎|看起来)[^.;|。；]{0,35}$",
            prefix,
            re.I,
        )
    )


EXACT_IDENTIFIER_RE = re.compile(
    r"`(?P<quoted>[A-Za-z_][A-Za-z0-9_.\[\]-]*)`|"
    r"\b(?P<camel>[a-z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)+)\b|"
    r"\b(?P<delimited>[A-Za-z][A-Za-z0-9]*(?:[_-][A-Za-z0-9]+)+)\b|"
    r"\b(?P<path>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\])+)+\b|"
    r"\b(?P<upper>[A-Z][A-Z0-9_]{2,})\b"
)
GENERIC_EXACT_IDENTIFIERS = {
    "api", "aws", "eapi", "http", "https", "json", "lambda", "null",
    "sapi", "papi", "true", "false", "unknown", "confirmed", "inferred",
}
STATE_LITERAL_PATTERNS = (
    re.compile(
        r"\b(?:status|(?:business\s+)?state)\b[^.!?。！？|]{0,35}"
        r"\b(?:becomes?|changes?(?:\s+to)?|transitions?(?:\s+to)?|(?:is\s+)?set\s+to)\s+"
        r"[`\"']?(?P<value>[A-Za-z0-9_.-]+)",
        re.I,
    ),
    re.compile(
        r"\b(?:sets?|changes?|transitions?)\s+(?:the\s+)?(?:status|(?:business\s+)?state)"
        r"(?:\s+from\s+[`\"']?[A-Za-z0-9_.-]+[`\"']?)?\s+to\s+"
        r"[`\"']?(?P<value>[A-Za-z0-9_.-]+)",
        re.I,
    ),
    re.compile(r"(?:业务状态|状态)[^。！？|]{0,20}(?:变更为|转换为|成为|设为)\s*[`\"']?(?P<value>[A-Za-z0-9_.\u3400-\u9fff-]+)", re.I),
    re.compile(r"(?:设置|变更|转换)(?:业务状态|状态)为\s*[`\"']?(?P<value>[A-Za-z0-9_.\u3400-\u9fff-]+)", re.I),
)
MAPPING_PAIR_RE = re.compile(
    r"\b(?:maps?|mapped|mapping|renames?|converts?)\s+`?(?P<source>[A-Za-z_][A-Za-z0-9_.\[\]-]*)`?"
    r"\s+(?:to|into|as|->)\s+`?(?P<target>[A-Za-z_][A-Za-z0-9_.\[\]-]*)`?",
    re.I,
)
DEFAULT_LITERAL_RE = re.compile(
    r"\b(?:(?:defaults?|falls?\s+back)\s+to|(?:has\s+(?:a\s+)?default|default)\s+(?:of|is|=))\s+"
    r"(?P<value>`[^`]+`|\"[^\"]+\"|'[^']+'|true|false|null|-?\d+(?:\.\d+)?(?:ms|s|m|h|d)?|[A-Z][A-Z0-9_.-]+)(?=\s|[.,;:!?)]|$)|"
    r"默认(?:为|值(?:为)?)\s*(?P<zh_value>`[^`]+`|\"[^\"]+\"|'[^']+'|true|false|null|-?\d+(?:\.\d+)?(?:ms|s|m|h|d)?|[A-Za-z0-9_.-]+)",
    re.I,
)
MONEY_TOKEN_RE = re.compile(
    r"(?:[$€£¥]\s*\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(?:USD|EUR|GBP|CNY|RMB|HKD|JPY|SGD|AUD|CAD|CHF|NZD))",
    re.I,
)
BARE_MONEY_RE = re.compile(
    r"\b(?:amount|fee|balance|payment)\b\s*(?:is|=|of|:)?\s*"
    r"(?P<value>-?\d[\d,]*(?:\.\d+)?)",
    re.I,
)
CURRENCY_RE = re.compile(r"\b(?:USD|EUR|GBP|CNY|RMB|HKD|JPY|SGD|AUD|CAD|CHF|NZD)\b", re.I)
PERSIST_OBJECT_RE = re.compile(
    r"\b(?:persists?|stores?|commits?|writes?)\s+(?:the\s+|an?\s+)?(?P<object>[^.;|。；]{1,60})",
    re.I,
)
GENERIC_OBJECT_WORDS = {
    "a", "an", "and", "data", "entity", "information", "item", "object", "record",
    "result", "state", "the", "to", "using", "value", "with", "write", "writes",
}
OBJECT_ALIASES = {"client": "customer", "clients": "customer", "customers": "customer"}


def claim_fact_corpus(claims: list[dict[str, object]]) -> str:
    values: list[str] = []
    for claim in claims:
        values.append(str(claim.get("statement", "")))
        render_terms = claim.get("render_terms")
        if isinstance(render_terms, list):
            values.extend(str(term) for term in render_terms)
        verification = claim.get("verification")
        if isinstance(verification, dict) and isinstance(verification.get("tokens"), list):
            values.extend(str(token) for token in verification["tokens"])
    return " ".join(values)


def exact_identifiers(value: str) -> set[str]:
    identifiers: set[str] = set()
    for match in EXACT_IDENTIFIER_RE.finditer(value):
        token = next(group for group in match.groups() if group is not None).lower()
        if token not in GENERIC_EXACT_IDENTIFIERS:
            identifiers.add(token)
    return identifiers


def state_literals(value: str) -> set[str]:
    return {
        match.group("value").strip("`\"'").rstrip(".").lower()
        for pattern in STATE_LITERAL_PATTERNS
        for match in pattern.finditer(value)
    }


def default_literals(value: str) -> set[str]:
    result: set[str] = set()
    for match in DEFAULT_LITERAL_RE.finditer(value):
        token = match.group("value") or match.group("zh_value")
        if token:
            result.add(token.strip("`\"'").lower())
    return result


def monetary_literals(value: str) -> set[str]:
    result = {re.sub(r"[\s,]", "", token).lower() for token in MONEY_TOKEN_RE.findall(value)}
    result.update(
        re.sub(r",", "", match.group("value")).lower()
        for match in BARE_MONEY_RE.finditer(value)
    )
    return result


def mapping_pairs(value: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for match in MAPPING_PAIR_RE.finditer(value):
        source = match.group("source").rstrip(".")
        target = match.group("target").rstrip(".")
        if exact_identifiers(source) and exact_identifiers(target):
            pairs.add((source.lower(), target.lower()))
    return pairs


def meaningful_object_tokens(value: str) -> set[str]:
    tokens = {
        OBJECT_ALIASES.get(token.lower(), token.lower())
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]*|[\u3400-\u9fff]{2,}", value)
    }
    return {token for token in tokens if token not in GENERIC_OBJECT_WORDS and len(token) > 2}


def persistence_object_tokens(value: str) -> set[str]:
    result: set[str] = set()
    for match in PERSIST_OBJECT_RE.finditer(value):
        object_value = re.split(
            r"\b(?:to|into|in|after|before|when|using|with|through)\b",
            match.group("object"),
            maxsplit=1,
            flags=re.I,
        )[0]
        result.update(meaningful_object_tokens(object_value))
    return result


def exact_material_value_findings(
    rendered: str,
    supporting: list[dict[str, object]],
    semantic_label: str,
    context: str,
) -> list[str]:
    """Protect exact values and objects while leaving ordinary prose wording free."""

    errors: list[str] = []
    corpus = claim_fact_corpus(supporting)

    def require_subset(rendered_values: set[str], claim_values: set[str], label: str) -> None:
        missing = sorted(rendered_values - claim_values)
        if missing:
            errors.append(
                f"{context}: material {semantic_label} uses {label} not present in its Claims: "
                + ", ".join(missing)
            )

    if semantic_label == "consumer-visible HTTP outcome":
        require_subset(
            set(re.findall(r"(?<!\d)[1-5]\d\d(?!\d)", rendered)),
            set(re.findall(r"(?<!\d)[1-5]\d\d(?!\d)", corpus)),
            "HTTP status value(s)",
        )
    elif semantic_label == "business state transition":
        require_subset(state_literals(rendered), state_literals(corpus), "state literal(s)")
    elif semantic_label == "field mapping":
        rendered_pairs = mapping_pairs(rendered)
        claim_pairs = mapping_pairs(corpus)
        claim_ids = exact_identifiers(corpus)
        missing_pairs = sorted(
            pair for pair in rendered_pairs
            if pair not in claim_pairs and not ({pair[0], pair[1]} <= claim_ids)
        )
        if missing_pairs:
            errors.append(
                f"{context}: material field mapping uses source/target pair(s) not present in its Claims: "
                + ", ".join(f"{source}->{target}" for source, target in missing_pairs)
            )
    elif semantic_label == "default value":
        require_subset(default_literals(rendered), default_literals(corpus), "default literal(s)")
    elif semantic_label == "configuration effect":
        require_subset(exact_identifiers(rendered), exact_identifiers(corpus), "configuration key(s)")
    elif semantic_label == "validation rule":
        require_subset(exact_identifiers(rendered), exact_identifiers(corpus), "field/rule identifier(s)")
    elif semantic_label == "monetary behavior":
        require_subset(monetary_literals(rendered), monetary_literals(corpus), "monetary literal(s)")
        require_subset(
            {token.lower() for token in CURRENCY_RE.findall(rendered)},
            {token.lower() for token in CURRENCY_RE.findall(corpus)},
            "currency value(s)",
        )
    elif semantic_label == "persistence/commit":
        rendered_objects = persistence_object_tokens(rendered)
        claim_objects = persistence_object_tokens(corpus) | meaningful_object_tokens(corpus)
        if rendered_objects and claim_objects and not (rendered_objects & claim_objects):
            errors.append(
                f"{context}: material persistence/commit changes the persisted object from its Claims: "
                + ", ".join(sorted(rendered_objects))
            )
    return errors


def material_semantic_findings(
    value: str,
    bound_claims: list[dict[str, object]],
    context: str,
) -> tuple[list[str], list[str]]:
    """Check material meaning by subject-scoped Claim category, not literal prose wording."""

    errors: list[str] = []
    warnings: list[str] = []
    rendered_exact = CLAIM_MARKER_RE.sub("", value)
    normalized = rendered_exact.lower()
    segments = re.split(r"\||(?<=[.!?。！？])\s+|\n+", normalized)
    for semantic_pattern, semantic_label, compatible_types, needs_high_risk in NARRATIVE_MATERIAL_RULES:
        matches: list[tuple[str, re.Match[str]]] = []
        for segment in segments:
            for semantic_match in semantic_pattern.finditer(segment):
                if semantic_match_is_qualified(segment, semantic_match):
                    continue
                matches.append((segment, semantic_match))
        if not matches:
            continue

        supporting = [
            claim
            for claim in bound_claims
            if claim.get("status") != "Unknown"
            and (
                claim.get("claim_type") in compatible_types
                or semantic_pattern.search(str(claim.get("statement", "")))
            )
            and (not needs_high_risk or claim.get("risk") == "high")
        ]
        if not supporting:
            errors.append(
                f"{context}: adds material {semantic_label} semantics without a compatible passing Claim"
            )
            continue

        errors.extend(
            exact_material_value_findings(
                rendered_exact, supporting, semantic_label, context
            )
        )

        has_unqualified = any(
            not semantic_match_is_tentative(segment, semantic_match)
            for segment, semantic_match in matches
        )
        if has_unqualified and not any(claim.get("status") == "Confirmed" for claim in supporting):
            errors.append(
                f"{context}: states material {semantic_label} as established, but its compatible Claims are only Inferred/Conflicting"
            )
        elif not has_unqualified and all(claim.get("status") == "Conflicting" for claim in supporting):
            warnings.append(
                f"{context}: tentative {semantic_label} language is backed only by Conflicting Claims; review whether the conflict is visible"
            )
    return errors, warnings


def text_sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def claim_sha256(claim: dict[str, object]) -> str:
    canonical = json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text_sha256(canonical)


def canonical_excerpt(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1 : end]) + "\n"


def resolve_inside(root: Path, relative: str) -> Path:
    root = root.expanduser().resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {relative}") from exc
    return target


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("YAML frontmatter is not closed with ---")
    return text[4:end], text[end + 5 :]


def list_values(frontmatter: str, key: str) -> list[str]:
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        match = re.match(rf"^{re.escape(key)}:\s*(.*?)\s*$", line)
        if not match:
            continue
        inline = match.group(1)
        if inline == "[]" or inline.lower() in {"null", "none"}:
            return []
        if inline.startswith("[") and inline.endswith("]"):
            return [item.strip().strip("\"'") for item in inline[1:-1].split(",") if item.strip()]
        values: list[str] = []
        for nested in lines[index + 1 :]:
            if nested and not nested[0].isspace():
                break
            item = re.match(r"^\s+-\s*[\"']?([^\"'\n]+?)[\"']?\s*$", nested)
            if item:
                values.append(item.group(1).strip())
        return values
    return []


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def pack_format_version(pack: Path) -> int:
    """Return 1 for a legacy manifest without a version, otherwise its integer version."""

    manifest = pack / "knowledge-manifest.yaml"
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return 1
    value = scalar_value(text, "pack_format_version")
    if value is None:
        return 1
    try:
        return int(value)
    except ValueError:
        return 0


def document_profile(document: Path, pack: Path) -> str:
    """Classify a v2 Markdown document without making prose structure a schema."""

    relative = document.resolve().relative_to(pack.resolve()).as_posix()
    if relative in NARRATIVE_ROOT_DOCUMENTS:
        return "narrative"
    if relative.startswith("tech-pack/behaviors/") and relative.endswith(".md"):
        return "narrative"
    if relative.startswith("ba-pack/") and relative.endswith(".md"):
        return "narrative"
    return "reference"


def narrative_semantic_text(body: str) -> str:
    """Collect Narrative assertions while ignoring template headings and fenced implementation."""

    body = re.sub(r"```.*?```", " ", body, flags=re.S)
    raw_lines = body.splitlines()
    lines: list[str] = []
    for index, line in enumerate(raw_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading:
            title = heading.group(1).strip()
            if title in STRUCTURAL_HEADINGS:
                continue
            stripped = title
        elif stripped.startswith("|"):
            if TABLE_SEPARATOR_RE.match(stripped):
                continue
            next_line = raw_lines[index + 1].strip() if index + 1 < len(raw_lines) else ""
            if TABLE_SEPARATOR_RE.match(next_line):
                continue
            stripped = " ".join(cell.strip() for cell in stripped.strip("|").split("|") if cell.strip())
        if is_pure_navigation(stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def marker_ids(value: str) -> list[str]:
    ids: list[str] = []
    for match in CLAIM_MARKER_RE.finditer(value):
        ids.extend(token for token in re.split(r"[\s,]+", match.group("ids")) if token)
    return ids


def is_pure_navigation(line: str) -> bool:
    value = LIST_ITEM_RE.sub("", line.strip())
    value = re.sub(r"\[[^\]]+\]\([^)]+\)", "", value)
    value = re.sub(r"[`*_—–:;,.()\[\]{}|/\\\s]+", "", value)
    return not value


def material_blocks(body: str) -> list[tuple[int, str, str]]:
    """Return (line, kind, text) for factual blocks requiring a claim marker."""

    lines = body.splitlines()
    blocks: list[tuple[int, str, str]] = []
    paragraph: list[str] = []
    paragraph_start = 0
    in_fence = False
    fence_language = ""
    fence_start = 0
    fence_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph, paragraph_start
        if paragraph:
            value = "\n".join(paragraph).strip()
            if value and not is_pure_navigation(value):
                blocks.append((paragraph_start, "paragraph", value))
        paragraph = []
        paragraph_start = 0

    for index, line in enumerate(lines, start=1):
        fence = FENCE_RE.match(line)
        if in_fence:
            if fence:
                if any(item.strip() for item in fence_lines):
                    before = lines[fence_start - 2] if fence_start >= 2 else ""
                    after = lines[index] if index < len(lines) else ""
                    rendered = "\n".join(fence_lines)
                    adjacent_markers = "\n".join(
                        value for value in (before, after) if marker_ids(value)
                    )
                    blocks.append((fence_start, "code block", rendered + "\n" + adjacent_markers))
                in_fence = False
                fence_language = ""
                fence_lines = []
                fence_start = 0
            else:
                fence_lines.append(line)
            continue
        if fence:
            flush_paragraph()
            in_fence = True
            fence_language = fence.group("language") or ""
            fence_start = index
            fence_lines = []
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith("#"):
            flush_paragraph()
            match = re.match(r"^#{1,6}\s+(.*?)\s*$", stripped)
            if match:
                heading = CLAIM_MARKER_RE.sub("", match.group(1)).strip()
                if heading not in STRUCTURAL_HEADINGS:
                    blocks.append((index, "heading", stripped))
            continue
        if stripped in {"---", "***", "___"}:
            flush_paragraph()
            continue
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            if paragraph:
                paragraph.append(line)
            continue
        if stripped.startswith("> This document describes"):
            flush_paragraph()
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            if TABLE_SEPARATOR_RE.match(stripped):
                continue
            next_line = lines[index] if index < len(lines) else ""
            if TABLE_SEPARATOR_RE.match(next_line.strip()):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) <= 2 and any(re.search(r"\[[^\]]+\]\([^)]+\)", cell) for cell in cells):
                continue
            blocks.append((index, "table row", line))
            continue
        if LIST_ITEM_RE.match(line):
            flush_paragraph()
            if not is_pure_navigation(line) and not stripped.startswith("- Repository commit:"):
                blocks.append((index, "list item", line))
            continue
        if not paragraph:
            paragraph_start = index
        paragraph.append(line)

    flush_paragraph()
    if in_fence:
        blocks.append((fence_start, "unclosed code block", "\n".join(fence_lines)[:240]))
    return blocks


def markdown_table_cells(line: str) -> list[str]:
    return [CLAIM_MARKER_RE.sub("", cell).strip() for cell in line.strip().strip("|").split("|")]


def claim_text_corpus(bound_claims: list[dict[str, object]]) -> str:
    values: list[str] = []
    for claim in bound_claims:
        values.append(str(claim.get("statement", "")))
        for key in ("render_terms", "subject_ids"):
            raw = claim.get(key)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
        verification = claim.get("verification")
        if isinstance(verification, dict) and isinstance(verification.get("tokens"), list):
            values.extend(str(item) for item in verification["tokens"])
    return " ".join(values).lower()


def validate_field_catalog_cells(
    body: str,
    relative: str,
    claims: dict[str, dict[str, object]],
) -> list[str]:
    """Reject unsupported field type/requiredness/nullability/ownership facts."""

    errors: list[str] = []
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|") or index + 1 >= len(lines):
            continue
        headers = markdown_table_cells(line)
        if "Field ID" not in headers or "Meaning" not in headers:
            continue
        if not TABLE_SEPARATOR_RE.match(lines[index + 1].strip()):
            continue
        header_index = {header: position for position, header in enumerate(headers)}
        row_index = index + 2
        while row_index < len(lines) and lines[row_index].lstrip().startswith("|"):
            row = lines[row_index]
            cells = markdown_table_cells(row)
            ids = marker_ids(row)
            bound_claims = [claims[claim_id] for claim_id in ids if claim_id in claims]
            corpus = claim_text_corpus(bound_claims)
            field_id = cells[header_index["Field ID"]] if len(cells) > header_index["Field ID"] else "field row"

            type_header = next((name for name in ("Type/format", "Type", "Format") if name in header_index), None)
            if type_header and len(cells) > header_index[type_header]:
                value = cells[header_index[type_header]]
                if value not in {"", "—", "-", "Unknown", "N/A"}:
                    tokens = [
                        token.lower()
                        for token in re.findall(r"[A-Za-z][A-Za-z0-9_.-]*|\d+", value)
                        if token.lower() not in {"observed", "literal", "literals", "and", "or", "type", "format"}
                    ]
                    if tokens and not any(token in corpus for token in tokens):
                        errors.append(
                            f"{relative}:{row_index + 1}: {field_id} {type_header} value is not asserted by its bound claims: {value}"
                        )

            sensitive_columns = {
                "Meaning": re.compile(r"\b(?:owner|ownership|crm|system\s+of\s+record|master\s+record|canonical\s+record)\b|所有者|主记录|权威记录", re.I),
                "Required": re.compile(r"\b(?:required|mandatory|must\s+be\s+present|always\s+present)\b|必填|必须存在", re.I),
                "Nullable": re.compile(r"\b(?:nullable|non[- ]?null|never\s+null|nullability)\b|可空|非空", re.I),
                "Source/default": re.compile(r"\b(?:default|owner|crm|system\s+of\s+record|master\s+record|canonical\s+record)\b|默认|所有者|主记录|权威记录", re.I),
                "Sensitivity": re.compile(r"\b(?:pii|personal|confidential|secret|sensitive|restricted)\b|敏感|机密|个人信息", re.I),
            }
            for column, pattern in sensitive_columns.items():
                position = header_index.get(column)
                if position is None or len(cells) <= position:
                    continue
                value = cells[position]
                matches = [match.group(0).lower() for match in pattern.finditer(value)]
                if matches and any(match not in corpus for match in matches):
                    errors.append(
                        f"{relative}:{row_index + 1}: {field_id} {column} adds a field semantic not asserted by its bound claims: {value}"
                    )
            row_index += 1
        break
    return errors


def claim_document_paths(pack: Path) -> list[Path]:
    result: list[Path] = []
    for root_document in ("knowledge-map.md", "coverage-report.md"):
        path = pack / root_document
        if path.is_file():
            result.append(path)
    for area in (pack / "tech-pack", pack / "ba-pack"):
        if area.is_dir():
            result.extend(sorted(area.rglob("*.md")))
    return result


def find_pack_root(document: Path) -> Path | None:
    resolved = document.expanduser().resolve()
    for candidate in (resolved.parent, *resolved.parents):
        if (candidate / "knowledge-manifest.yaml").is_file() and (candidate / ".work").is_dir():
            return candidate
    return None


def validate_single_document(
    document: Path,
    repo: Path,
) -> tuple[list[str], list[str]]:
    pack = find_pack_root(document)
    if pack is None:
        return ["document is not inside a knowledge pack with .work claim artifacts"], []
    try:
        frontmatter, _body = split_frontmatter(document.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read document identity for claim validation: {exc}"], []
    artifact_errors, artifact_warnings, claims = validate_claim_artifacts(
        pack / ".work" / "claim-ledger.json",
        pack / ".work" / "claim-audit.json",
        repo,
        scalar_value(frontmatter, "repository"),
        scalar_value(frontmatter, "source_commit"),
    )
    if artifact_errors:
        return artifact_errors, artifact_warnings
    if pack_format_version(pack) >= 2:
        if document_profile(document, pack) == "narrative":
            document_errors, document_warnings, _used = validate_narrative_document_claims(
                document, pack, claims
            )
        else:
            document_errors, document_warnings, _used = validate_v2_reference_document_claims(
                document, pack, claims
            )
    else:
        document_errors, document_warnings, _used = validate_document_claims(document, pack, claims)
    return artifact_errors + document_errors, artifact_warnings + document_warnings


def validate_narrative_document_claims(
    document: Path,
    pack: Path,
    claims: dict[str, dict[str, object]],
) -> tuple[list[str], list[str], set[str]]:
    """Validate v2 Narrative materiality without prescribing sentence wording."""

    errors: list[str] = []
    warnings: list[str] = []
    relative = document.resolve().relative_to(pack.resolve()).as_posix()
    try:
        frontmatter, body = split_frontmatter(document.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{relative}: cannot validate Narrative grounding: {exc}"], [], set()

    declared = list_values(frontmatter, "claim_ids")
    used = set(declared)
    if not declared:
        errors.append(
            f"{relative}: frontmatter claim_ids must contain the material fact set for Narrative content"
        )
    if len(declared) != len(set(declared)):
        errors.append(f"{relative}: frontmatter claim_ids contains duplicates")
    bound_claims: list[dict[str, object]] = []
    behavior_id = scalar_value(frontmatter, "behavior_id")
    behavior_scoped = relative.startswith(("tech-pack/behaviors/", "ba-pack/behaviors/"))
    for claim_id in declared:
        claim = claims.get(claim_id)
        if claim is None:
            errors.append(f"{relative}: frontmatter references unknown claim: {claim_id}")
        else:
            bound_claims.append(claim)
            if behavior_scoped and behavior_id:
                subjects = claim.get("subject_ids")
                if not isinstance(subjects, list) or behavior_id not in subjects:
                    errors.append(
                        f"{relative}: Narrative claim {claim_id} is not bound to behavior {behavior_id}"
                    )

    # Legacy invisible markers are tolerated in a v2 Narrative during migration,
    # but they may not introduce undeclared or unknown Claims.
    for claim_id in marker_ids(body):
        if claim_id not in claims:
            errors.append(f"{relative}: body marker references unknown claim: {claim_id}")
        elif claim_id not in declared:
            errors.append(
                f"{relative}: body marker claim is missing from frontmatter claim_ids: {claim_id}"
            )

    material_errors, material_warnings = material_semantic_findings(
        narrative_semantic_text(body), bound_claims, f"{relative}: Narrative"
    )
    errors.extend(material_errors)
    warnings.extend(material_warnings)

    if "SCAFFOLD_ONLY" in body:
        errors.append(f"{relative}: scaffold-only sentinel remains")
    return errors, warnings, used


def validate_v2_reference_document_claims(
    document: Path,
    pack: Path,
    claims: dict[str, dict[str, object]],
) -> tuple[list[str], list[str], set[str]]:
    """Keep rows/examples exact while allowing natural Reference summaries."""

    errors, warnings, used = validate_narrative_document_claims(document, pack, claims)
    relative = document.resolve().relative_to(pack.resolve()).as_posix()
    try:
        _frontmatter, body = split_frontmatter(document.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return errors, warnings, used

    for line, kind, block in material_blocks(body):
        if kind not in {"table row", "code block"}:
            continue
        block_claim_ids = marker_ids(block)
        if not block_claim_ids:
            preview = " ".join(block.split())[:140]
            errors.append(f"{relative}:{line}: structured {kind} has no claim marker: {preview}")
            continue
        normalized_block = CLAIM_MARKER_RE.sub("", block).lower()
        bound_claims = [claims[claim_id] for claim_id in block_claim_ids if claim_id in claims]
        for claim_id in block_claim_ids:
            claim = claims.get(claim_id)
            if claim is None:
                errors.append(f"{relative}:{line}: structured {kind} references unknown claim: {claim_id}")
                continue
            render_terms = claim.get("render_terms")
            if not isinstance(render_terms, list) or not any(
                isinstance(term, str) and term.lower() in normalized_block for term in render_terms
            ):
                errors.append(
                    f"{relative}:{line}: structured {kind} does not contain a render term for {claim_id}"
                )
        semantic_segments = re.split(r"\||(?<=[.!?。！？])\s+", normalized_block)
        for semantic_pattern, _evidence_pattern, semantic_label in SEMANTIC_EVIDENCE_RULES:
            unsupported = any(
                not semantic_match_is_qualified(segment, semantic_match)
                and not any(
                    semantic_pattern.search(str(claim.get("statement", "")))
                    for claim in bound_claims
                )
                for segment in semantic_segments
                for semantic_match in semantic_pattern.finditer(segment)
            )
            if unsupported:
                errors.append(
                    f"{relative}:{line}: structured {kind} adds {semantic_label} semantics "
                    "not asserted by its bound claims"
                )

    if relative == "tech-pack/fields/field-catalog.md":
        errors.extend(validate_field_catalog_cells(body, relative, claims))
    return errors, warnings, used


def validate_document_claims(
    document: Path,
    pack: Path,
    claims: dict[str, dict[str, object]],
) -> tuple[list[str], list[str], set[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    used: set[str] = set()
    relative = document.resolve().relative_to(pack.resolve()).as_posix()
    try:
        frontmatter, body = split_frontmatter(document.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{relative}: cannot validate claim coverage: {exc}"], [], set()

    declared = list_values(frontmatter, "claim_ids")
    if not declared:
        errors.append(f"{relative}: frontmatter claim_ids must list every rendered repository claim")
    if len(declared) != len(set(declared)):
        errors.append(f"{relative}: frontmatter claim_ids contains duplicates")
    for claim_id in declared:
        if claim_id not in claims:
            errors.append(f"{relative}: frontmatter references unknown claim: {claim_id}")

    marker_occurrences = marker_ids(body)
    used.update(marker_occurrences)
    for claim_id in marker_occurrences:
        if claim_id not in claims:
            errors.append(f"{relative}: body marker references unknown claim: {claim_id}")
        if claim_id not in declared:
            errors.append(f"{relative}: body marker claim is missing from frontmatter claim_ids: {claim_id}")
    for claim_id in declared:
        if claim_id not in used:
            errors.append(f"{relative}: declared claim is never attached to a factual block: {claim_id}")

    for line, kind, block in material_blocks(body):
        block_claim_ids = marker_ids(block)
        auditable_text = CLAIM_MARKER_RE.sub("", block)
        auditable_text = LIST_ITEM_RE.sub("", auditable_text.strip())
        if kind in {"paragraph", "list item", "heading"} and MULTI_SENTENCE_RE.search(auditable_text):
            errors.append(
                f"{relative}:{line}: factual {kind} contains multiple sentences; split and bind each sentence separately"
            )
        if not block_claim_ids:
            preview = " ".join(block.split())[:140]
            errors.append(f"{relative}:{line}: factual {kind} has no claim marker: {preview}")
            continue
        normalized_block = CLAIM_MARKER_RE.sub("", block).lower()
        bound_claims = [claims[claim_id] for claim_id in block_claim_ids if claim_id in claims]
        for claim_id in block_claim_ids:
            claim = claims.get(claim_id)
            if claim is None:
                continue
            render_terms = claim.get("render_terms")
            if not isinstance(render_terms, list) or not any(
                isinstance(term, str) and term.lower() in normalized_block for term in render_terms
            ):
                errors.append(
                    f"{relative}:{line}: factual {kind} does not contain a render term for {claim_id}"
                )
        semantic_segments = re.split(r"\||(?<=[.!?。！？])\s+", normalized_block)
        for semantic_pattern, _evidence_pattern, semantic_label in SEMANTIC_EVIDENCE_RULES:
            unsupported = False
            for segment in semantic_segments:
                for semantic_match in semantic_pattern.finditer(segment):
                    if semantic_match_is_qualified(segment, semantic_match):
                        continue
                    if not any(
                        semantic_pattern.search(str(claim.get("statement", "")))
                        for claim in bound_claims
                    ):
                        unsupported = True
            if unsupported:
                errors.append(
                    f"{relative}:{line}: factual {kind} adds {semantic_label} semantics "
                    "not asserted by its bound claims"
                )

    for mermaid_match in re.finditer(
        r"```mermaid\s*\n(?P<code>.*?)```(?P<after>\s*<!--\s*claims:.*?-->)?",
        body,
        re.I | re.S,
    ):
        mermaid = mermaid_match.group("code")
        node_count = len(re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\s*(?:\[[^\]]+\]|\{[^}]+\}|\([^)]+\))", mermaid))
        if node_count < 2:
            ids = marker_ids(mermaid_match.group("after") or "")
            all_unknown = bool(ids) and all(
                claim_id in claims and claims[claim_id].get("status") == "Unknown"
                for claim_id in ids
            )
            if node_count != 1 or not all_unknown:
                errors.append(
                    f"{relative}: Mermaid diagram must contain at least two claim-backed nodes, "
                    "or one node backed only by Unknown claims"
                )

    if relative == "tech-pack/fields/field-catalog.md":
        errors.extend(validate_field_catalog_cells(body, relative, claims))

    if "SCAFFOLD_ONLY" in body:
        errors.append(f"{relative}: scaffold-only sentinel remains")
    return errors, warnings, used


def _load_object(path: Path, label: str) -> tuple[dict[str, object] | None, list[str]]:
    if not path.is_file():
        return None, [f"{label} does not exist: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{label} is not valid JSON: {exc}"]
    if not isinstance(value, dict):
        return None, [f"{label} root must be an object"]
    return value, []


def validate_claim_artifacts(
    ledger_path: Path,
    audit_path: Path,
    repo: Path,
    expected_repository: str | None = None,
    expected_commit: str | None = None,
    require_audit: bool = True,
) -> tuple[list[str], list[str], dict[str, dict[str, object]]]:
    errors: list[str] = []
    warnings: list[str] = []
    claims_by_id: dict[str, dict[str, object]] = {}
    repo = repo.expanduser().resolve()

    ledger, load_errors = _load_object(ledger_path, "claim ledger")
    errors.extend(load_errors)
    audit: dict[str, object] | None = None
    if require_audit:
        audit, audit_load_errors = _load_object(audit_path, "claim audit")
        errors.extend(audit_load_errors)
    if ledger is None or (require_audit and audit is None):
        return errors, warnings, claims_by_id

    artifacts = [("claim ledger", ledger)]
    if audit is not None:
        artifacts.append(("claim audit", audit))
    for label, artifact in artifacts:
        allowed_top_level = {
            "claim ledger": {"schema_version", "repository", "source_commit", "claims"},
            "claim audit": {"schema_version", "repository", "source_commit", "review", "audits"},
        }[label]
        unexpected = sorted(set(artifact) - allowed_top_level - {"scaffold_state"})
        if unexpected:
            errors.append(f"{label} contains unexpected top-level key(s): " + ", ".join(unexpected))
        if artifact.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{label} schema_version must be {SCHEMA_VERSION}")
        if "scaffold_state" in artifact:
            errors.append(f"{label} still contains scaffold_state")
        if expected_repository is not None and artifact.get("repository") != expected_repository:
            errors.append(f"{label} repository does not match manifest")
        if expected_commit is not None and artifact.get("source_commit") != expected_commit:
            errors.append(f"{label} source_commit does not match manifest")

    claims = ledger.get("claims")
    if not isinstance(claims, list):
        errors.append("claim ledger claims must be a list")
        claims = []
    for index, claim in enumerate(claims, start=1):
        label = f"claim {index}"
        if not isinstance(claim, dict):
            errors.append(f"{label} must be an object")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            errors.append(f"{label} has invalid claim_id")
            continue
        label = claim_id
        if claim_id in claims_by_id:
            errors.append(f"duplicate claim_id: {claim_id}")
            continue
        claims_by_id[claim_id] = claim

        required = {
            "claim_id", "subject_ids", "claim_type", "statement", "status", "risk",
            "reasoning", "needed_evidence", "search_scope", "verification", "render_terms", "evidence",
        }
        missing = sorted(required - set(claim))
        unexpected_claim_keys = sorted(set(claim) - required)
        if missing:
            errors.append(f"{label} missing key(s): " + ", ".join(missing))
        if unexpected_claim_keys:
            errors.append(f"{label} contains unexpected key(s): " + ", ".join(unexpected_claim_keys))
        subject_ids = claim.get("subject_ids")
        if not isinstance(subject_ids, list) or any(not isinstance(item, str) or not item for item in subject_ids):
            errors.append(f"{label} subject_ids must be a list of nonempty IDs")
        elif len(subject_ids) != len(set(subject_ids)):
            errors.append(f"{label} subject_ids contains duplicates")
        if claim.get("claim_type") not in CLAIM_TYPES:
            errors.append(f"{label} has invalid claim_type")
        statement = claim.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            errors.append(f"{label} statement must be nonempty")
        elif len(statement.strip()) < 15:
            errors.append(f"{label} statement is too short to be an auditable atomic assertion")
        if isinstance(statement, str):
            if MULTI_SENTENCE_RE.search(statement.strip()):
                errors.append(f"{label} statement contains multiple sentences; split it into atomic claims")
            compound_signals = len(COMPOUND_SIGNAL_RE.findall(statement))
            if (status := claim.get("status")) == "Unknown" and compound_signals >= 1:
                errors.append(f"{label} Unknown statement appears compound; split independent unknowns")
            elif compound_signals >= 2:
                errors.append(f"{label} statement appears compound; split it into atomic claims")
        status = claim.get("status")
        if status not in STATUSES:
            errors.append(f"{label} has invalid status")
        if claim.get("claim_type") == "other" and status != "Unknown":
            errors.append(f"{label} claim_type other is allowed only for Unknown gaps; choose a specific type")
        risk = claim.get("risk")
        if risk not in RISKS:
            errors.append(f"{label} risk must be normal or high")
        if claim.get("claim_type") in HIGH_RISK_TYPES and risk != "high":
            errors.append(f"{label} claim_type requires risk high")
        if isinstance(statement, str) and HIGH_RISK_RE.search(statement) and risk != "high":
            errors.append(f"{label} contains a high-risk assertion and must set risk to high")
        render_terms = claim.get("render_terms")
        if (
            not isinstance(render_terms, list)
            or not render_terms
            or any(not isinstance(term, str) or len(term.strip()) < 2 for term in render_terms)
        ):
            errors.append(f"{label} render_terms must contain one or more nontrivial strings")
        elif all(term.strip().lower() in GENERIC_RENDER_TERMS for term in render_terms):
            errors.append(f"{label} render_terms are too generic to bind document text")

        reasoning = claim.get("reasoning")
        needed = claim.get("needed_evidence")
        if status in {"Inferred", "Conflicting", "Unknown"}:
            if not isinstance(reasoning, str) or not reasoning.strip():
                errors.append(f"{label} {status} status requires reasoning")
            if not isinstance(needed, str) or not needed.strip():
                errors.append(f"{label} {status} status requires needed_evidence")
        if status == "Unknown" and isinstance(statement, str) and not UNKNOWN_SIGNAL_RE.search(statement):
            errors.append(f"{label} Unknown statement must explicitly express uncertainty or a question")
        if claim.get("claim_type") == "absence":
            search_scope = claim.get("search_scope")
            if not isinstance(search_scope, str) or not search_scope.strip():
                errors.append(f"{label} absence claim requires a nonempty search_scope")

        evidence = claim.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{label} evidence must be a list")
            evidence = []
        supports_direct: list[dict[str, object]] = []
        supports_any: list[dict[str, object]] = []
        contradicts: list[dict[str, object]] = []
        seen_sources: set[str] = set()
        evidence_text_by_source: dict[str, str] = {}
        supporting_sources: set[str] = set()
        direct_supporting_sources: set[str] = set()
        for evidence_index, item in enumerate(evidence, start=1):
            evidence_label = f"{label} evidence {evidence_index}"
            if not isinstance(item, dict):
                errors.append(f"{evidence_label} must be an object")
                continue
            required_evidence = {"source", "source_kind", "relation", "support_level", "excerpt_sha256", "rationale"}
            missing_evidence = sorted(required_evidence - set(item))
            unexpected_evidence = sorted(set(item) - required_evidence)
            if missing_evidence:
                errors.append(f"{evidence_label} missing key(s): " + ", ".join(missing_evidence))
            if unexpected_evidence:
                errors.append(f"{evidence_label} contains unexpected key(s): " + ", ".join(unexpected_evidence))
            source_ref = item.get("source")
            source_kind = item.get("source_kind")
            relation = item.get("relation")
            support_level = item.get("support_level")
            excerpt_hash = item.get("excerpt_sha256")
            rationale = item.get("rationale")
            if source_kind not in SOURCE_KINDS:
                errors.append(f"{evidence_label} has invalid source_kind")
            if relation not in RELATIONS:
                errors.append(f"{evidence_label} has invalid relation")
            if support_level not in SUPPORT_LEVELS:
                errors.append(f"{evidence_label} has invalid support_level")
            if source_kind in {"comment", "naming"} and support_level == "direct":
                errors.append(f"{evidence_label} comment/naming evidence cannot be direct")
            if not isinstance(rationale, str) or len(rationale.strip()) < 20:
                errors.append(f"{evidence_label} rationale must explain the evidence-to-claim link")
            elif "REPLACE_" in rationale:
                errors.append(f"{evidence_label} still contains a scaffold rationale")
            if not isinstance(excerpt_hash, str) or not HASH_RE.fullmatch(excerpt_hash):
                errors.append(f"{evidence_label} has invalid excerpt_sha256")

            match = REFERENCE_RE.fullmatch(source_ref) if isinstance(source_ref, str) else None
            if not match:
                errors.append(f"{evidence_label} has invalid source reference")
                continue
            relative = match.group("path")
            relative_path = Path(relative)
            if relative_path.name in FORBIDDEN_EVIDENCE_NAMES or any(
                part in FORBIDDEN_EVIDENCE_PARTS for part in relative_path.parts
            ):
                errors.append(f"{evidence_label} points to generated metadata rather than repository evidence")
                continue
            start = int(match.group("start"))
            end = int(match.group("end") or start)
            try:
                source = resolve_inside(repo, relative)
            except ValueError as exc:
                errors.append(f"{evidence_label} {exc}")
                continue
            if not source.is_file():
                errors.append(f"{evidence_label} source file does not exist: {relative}")
                continue
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
            if start < 1 or end < start or end > len(lines):
                errors.append(f"{evidence_label} source range is outside file bounds")
                continue
            actual_hash = text_sha256(canonical_excerpt(lines, start, end))
            if excerpt_hash != actual_hash:
                errors.append(f"{evidence_label} excerpt hash is stale or incorrect")
            normalized_source = f"{relative}:{start}" + (f"-{end}" if end != start else "")
            evidence_text_by_source[normalized_source] = canonical_excerpt(lines, start, end)
            if normalized_source in seen_sources:
                errors.append(f"{label} repeats the same physical evidence range: {normalized_source}")
            seen_sources.add(normalized_source)
            if relation == "supports":
                supporting_sources.add(normalized_source)
                supports_any.append(item)
                if support_level == "direct":
                    direct_supporting_sources.add(normalized_source)
                    supports_direct.append(item)
            if relation == "contradicts":
                contradicts.append(item)

        if status == "Confirmed" and not supports_direct:
            errors.append(f"{label} Confirmed status requires direct supporting evidence")
        if status == "Inferred" and not supports_any:
            errors.append(f"{label} Inferred status requires supporting evidence")
        if status == "Conflicting" and (not supports_any or not contradicts):
            errors.append(f"{label} Conflicting status requires supporting and contradicting evidence")
        if status in {"Confirmed", "Inferred"} and contradicts:
            errors.append(f"{label} {status} status cannot carry contradicting evidence; use Conflicting")
        if status == "Unknown" and supports_direct:
            errors.append(f"{label} Unknown status must not carry direct supporting evidence for an affirmative statement")
        if risk == "high" and status == "Confirmed":
            independent = {
                str(item.get("source", "")).rsplit(":", 1)[0]
                for item in supports_direct
            }
            if len(independent) < 2:
                errors.append(
                    f"{label} high-risk Confirmed claim requires direct support from two distinct physical files"
                )

        verification = claim.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{label} verification must be an object")
        else:
            mode = verification.get("mode")
            tokens = verification.get("tokens")
            verification_sources = verification.get("evidence_sources")
            if mode not in VERIFICATION_MODES:
                errors.append(f"{label} verification has invalid mode")
            if not isinstance(tokens, list) or any(not isinstance(token, str) or not token.strip() for token in tokens):
                errors.append(f"{label} verification tokens must be a list of nonempty strings")
                tokens = []
            if not isinstance(verification_sources, list) or any(
                not isinstance(source, str) or not source for source in verification_sources
            ):
                errors.append(f"{label} verification evidence_sources must be a list of references")
                verification_sources = []
            if claim.get("claim_type") in MACHINE_REQUIRED_TYPES and mode == "manual" and status != "Unknown":
                errors.append(f"{label} structured claim type may not use manual verification")
            if mode in {"contains-all", "contains-any"}:
                if not tokens:
                    errors.append(f"{label} lexical verification requires at least one token")
                statement_lower = statement.lower() if isinstance(statement, str) else ""
                tokens_absent_from_statement = [
                    token for token in tokens
                    if isinstance(token, str) and token.lower() not in statement_lower
                ]
                if tokens_absent_from_statement:
                    errors.append(
                        f"{label} verification token(s) absent from claim statement: "
                        + ", ".join(tokens_absent_from_statement)
                    )
                generic_tokens = [
                    token for token in tokens
                    if isinstance(token, str) and token.strip().lower() in GENERIC_VERIFICATION_TERMS
                ]
                if generic_tokens:
                    errors.append(
                        f"{label} verification token(s) are too generic: " + ", ".join(generic_tokens)
                    )
                if not verification_sources:
                    errors.append(f"{label} lexical verification requires supporting evidence_sources")
                for source in verification_sources:
                    if source not in supporting_sources:
                        errors.append(f"{label} verification source is not supporting claim evidence: {source}")
                    if status == "Confirmed" and source not in direct_supporting_sources:
                        errors.append(f"{label} Confirmed verification source is not direct supporting evidence: {source}")
                combined = "\n".join(
                    evidence_text_by_source[source]
                    for source in verification_sources
                    if source in evidence_text_by_source
                ).lower()
                present = [token.lower() in combined for token in tokens]
                if mode == "contains-all" and present and not all(present):
                    missing_tokens = [token for token, found in zip(tokens, present) if not found]
                    errors.append(f"{label} verification token(s) absent from evidence: " + ", ".join(missing_tokens))
                if mode == "contains-any" and present and not any(present):
                    errors.append(f"{label} none of the verification tokens occur in supporting evidence")
                for statement_pattern, evidence_pattern, semantic_label in SEMANTIC_EVIDENCE_RULES:
                    if isinstance(statement, str) and statement_pattern.search(statement) and not evidence_pattern.search(combined):
                        errors.append(
                            f"{label} asserts {semantic_label} semantics absent from its supporting evidence"
                        )

    if not require_audit:
        return errors, warnings, claims_by_id

    assert audit is not None
    review = audit.get("review")
    if not isinstance(review, dict):
        errors.append("claim audit review must record an independent review context")
    else:
        required_review = {"mode", "author_id", "reviewer_id"}
        missing_review = sorted(required_review - set(review))
        unexpected_review = sorted(set(review) - required_review)
        if missing_review:
            errors.append("claim audit review missing key(s): " + ", ".join(missing_review))
        if unexpected_review:
            errors.append("claim audit review contains unexpected key(s): " + ", ".join(unexpected_review))
        if review.get("mode") not in AUDIT_REVIEW_MODES:
            errors.append("claim audit review.mode must be independent-subagent or separate-context")
        author_id = review.get("author_id")
        reviewer_id = review.get("reviewer_id")
        if not isinstance(author_id, str) or len(author_id.strip()) < 3:
            errors.append("claim audit review.author_id must identify the authoring context")
        if not isinstance(reviewer_id, str) or len(reviewer_id.strip()) < 3:
            errors.append("claim audit review.reviewer_id must identify the reviewing context")
        if isinstance(author_id, str) and isinstance(reviewer_id, str) and author_id.strip() == reviewer_id.strip():
            errors.append("claim audit author_id and reviewer_id must be different contexts")
    audits = audit.get("audits")
    if not isinstance(audits, list):
        errors.append("claim audit audits must be a list")
        audits = []
    audits_by_id: dict[str, dict[str, object]] = {}
    normalized_audit_notes: dict[str, list[str]] = {}
    for index, item in enumerate(audits, start=1):
        if not isinstance(item, dict):
            errors.append(f"audit {index} must be an object")
            continue
        claim_id = item.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in claims_by_id:
            errors.append(f"audit {index} references unknown claim_id: {claim_id}")
            continue
        if claim_id in audits_by_id:
            errors.append(f"duplicate audit for {claim_id}")
            continue
        audits_by_id[claim_id] = item
        required_audit = {
            "claim_id", "verdict", "reviewed_statement_sha256", "reviewed_evidence_hashes",
            "reviewed_claim_sha256", "entailment_notes", "overstatement_check",
        }
        missing_audit = sorted(required_audit - set(item))
        unexpected_audit = sorted(set(item) - required_audit)
        if missing_audit:
            errors.append(f"audit {claim_id} missing key(s): " + ", ".join(missing_audit))
        if unexpected_audit:
            errors.append(f"audit {claim_id} contains unexpected key(s): " + ", ".join(unexpected_audit))
        if item.get("verdict") not in AUDIT_VERDICTS:
            errors.append(f"audit {claim_id} has invalid verdict")
        elif item.get("verdict") != "Pass":
            errors.append(f"audit {claim_id} is not passing: {item.get('verdict')}")
        statement = str(claims_by_id[claim_id].get("statement", ""))
        if item.get("reviewed_statement_sha256") != text_sha256(statement):
            errors.append(f"audit {claim_id} statement hash is stale or incorrect")
        if item.get("reviewed_claim_sha256") != claim_sha256(claims_by_id[claim_id]):
            errors.append(f"audit {claim_id} full-claim hash is stale or incorrect")
        expected_hashes = sorted(
            str(evidence.get("excerpt_sha256"))
            for evidence in claims_by_id[claim_id].get("evidence", [])
            if isinstance(evidence, dict) and isinstance(evidence.get("excerpt_sha256"), str)
        )
        reviewed_hashes = item.get("reviewed_evidence_hashes")
        if not isinstance(reviewed_hashes, list) or sorted(reviewed_hashes) != expected_hashes:
            errors.append(f"audit {claim_id} reviewed_evidence_hashes do not match the claim")
        notes = item.get("entailment_notes")
        if not isinstance(notes, str) or len(notes.strip()) < 30:
            errors.append(f"audit {claim_id} entailment_notes must be nonempty")
        else:
            normalized_notes = " ".join(notes.lower().split())
            normalized_audit_notes.setdefault(normalized_notes, []).append(claim_id)
        if item.get("overstatement_check") != "Pass":
            errors.append(f"audit {claim_id} overstatement_check must be Pass")

    for claim_id in claims_by_id:
        if claim_id not in audits_by_id:
            errors.append(f"claim has no independent audit: {claim_id}")
    for note, claim_ids in normalized_audit_notes.items():
        if len(claim_ids) >= 3:
            errors.append(
                "claim audit reuses one templated entailment note across multiple claims: "
                + ", ".join(claim_ids)
            )
    return errors, warnings, claims_by_id


def validate_claim_pack(
    pack: Path,
    repo: Path,
    expected_repository: str | None = None,
    expected_commit: str | None = None,
) -> tuple[list[str], list[str], dict[str, dict[str, object]]]:
    pack = pack.expanduser().resolve()
    errors, warnings, claims = validate_claim_artifacts(
        pack / ".work" / "claim-ledger.json",
        pack / ".work" / "claim-audit.json",
        repo,
        expected_repository,
        expected_commit,
    )
    if errors:
        return errors, warnings, claims

    version = pack_format_version(pack)
    used: set[str] = set()
    for document in claim_document_paths(pack):
        if version >= 2:
            if document_profile(document, pack) == "narrative":
                document_errors, document_warnings, document_used = validate_narrative_document_claims(
                    document, pack, claims
                )
            else:
                document_errors, document_warnings, document_used = validate_v2_reference_document_claims(
                    document, pack, claims
                )
        else:
            document_errors, document_warnings, document_used = validate_document_claims(
                document, pack, claims
            )
        errors.extend(document_errors)
        warnings.extend(document_warnings)
        used.update(document_used)

    status_strength = {"Unknown": 0, "Conflicting": 1, "Inferred": 2, "Confirmed": 3}
    for model_path in sorted((pack / ".work" / "flow-models").glob("*.json")):
        relative = model_path.relative_to(pack).as_posix()
        try:
            model = json.loads(model_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: cannot validate claim bindings: {exc}")
            continue
        if not isinstance(model, dict):
            errors.append(f"{relative}: flow model root must be an object")
            continue
        behavior_id = model.get("behavior_id")
        caption_claims = (
            model.get("diagram_claim_ids")
            if version >= 2 and "diagram_claim_ids" in model
            else model.get("summary_claim_ids")
        )
        caption_value = model.get("diagram_caption") if version >= 2 else model.get("summary")
        bound_groups: list[tuple[str, object, str | None, list[str], str]] = [
            (
                "diagram caption" if version >= 2 else "summary",
                caption_claims,
                None,
                [],
                str(caption_value) if isinstance(caption_value, str) else "",
            ),
        ]
        nodes = model.get("nodes")
        if isinstance(nodes, list):
            for index, node in enumerate(nodes, start=1):
                if isinstance(node, dict):
                    evidence_refs = [
                        item for item in node.get("evidence", []) if isinstance(item, str)
                    ] if isinstance(node.get("evidence"), list) else []
                    bound_groups.append(
                        (
                            f"node {index}",
                            node.get("claim_ids"),
                            node.get("status") if isinstance(node.get("status"), str) else None,
                            evidence_refs,
                            str(node.get("label", "")),
                        )
                    )
        edges = model.get("edges")
        edge_labels: set[str] = set()
        if isinstance(edges, list):
            for index, edge in enumerate(edges, start=1):
                if not isinstance(edge, dict):
                    continue
                edge_label = f"edge {index}"
                edge_labels.add(edge_label)
                condition = edge.get("condition")
                bound_groups.append(
                    (
                        edge_label,
                        edge.get("claim_ids"),
                        None,
                        [],
                        str(condition) if isinstance(condition, str) else "",
                    )
                )
        for binding_label, raw_ids, rendered_status, evidence_refs, rendered_text in bound_groups:
            if not isinstance(raw_ids, list) or not raw_ids:
                errors.append(f"{relative}: {binding_label} has no claim IDs")
                continue
            bound_claims: list[dict[str, object]] = []
            for claim_id in raw_ids:
                if not isinstance(claim_id, str) or claim_id not in claims:
                    errors.append(f"{relative}: {binding_label} references unknown claim: {claim_id}")
                    continue
                used.add(claim_id)
                claim = claims[claim_id]
                bound_claims.append(claim)
                subjects = claim.get("subject_ids")
                if isinstance(behavior_id, str) and isinstance(subjects, list) and behavior_id not in subjects:
                    errors.append(f"{relative}: {binding_label} claim {claim_id} is not bound to behavior {behavior_id}")
            if rendered_status in status_strength and bound_claims:
                weakest = min(status_strength.get(str(claim.get("status")), 0) for claim in bound_claims)
                if status_strength[rendered_status] > weakest:
                    errors.append(f"{relative}: {binding_label} status is stronger than its source claim status")
            if evidence_refs and bound_claims:
                allowed_sources = {
                    str(item.get("source"))
                    for claim in bound_claims
                    for item in claim.get("evidence", [])
                    if isinstance(item, dict) and isinstance(item.get("source"), str)
                }
                for evidence_ref in evidence_refs:
                    if evidence_ref not in allowed_sources:
                        errors.append(
                            f"{relative}: {binding_label} evidence is not owned by its bound claims: {evidence_ref}"
                        )
            if version >= 2 and rendered_text and bound_claims:
                material_errors, material_warnings = material_semantic_findings(
                    rendered_text,
                    bound_claims,
                    f"{relative}: {binding_label}",
                )
                errors.extend(material_errors)
                warnings.extend(material_warnings)
            if binding_label in edge_labels and bound_claims and all(
                claim.get("status") == "Unknown" for claim in bound_claims
            ):
                errors.append(
                    f"{relative}: {binding_label} cannot render order or causality from Unknown claims only"
                )
    if version < 2:
        for claim_id in sorted(set(claims) - used):
            warnings.append(f"approved claim is not rendered in a claim-bearing Markdown document: {claim_id}")
    return errors, warnings, claims


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--pack", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--repository")
    parser.add_argument("--source-commit")
    parser.add_argument("--draft", action="store_true", help="validate claims and evidence before claim audit")
    args = parser.parse_args()

    if args.pack:
        if args.draft:
            print("ERROR: --draft is supported only with --ledger and --audit")
            return 2
        errors, warnings, claims = validate_claim_pack(
            args.pack,
            args.repo,
            args.repository,
            args.source_commit,
        )
    elif args.ledger and args.audit:
        errors, warnings, claims = validate_claim_artifacts(
            args.ledger,
            args.audit,
            args.repo,
            args.repository,
            args.source_commit,
            not args.draft,
        )
    else:
        print("ERROR: provide --pack or both --ledger and --audit")
        return 2

    for warning in sorted(set(warnings)):
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(set(warnings))} warning(s)")
        return 1
    if args.draft:
        print(f"OK: draft claim schema, evidence ranges, and hashes are valid (claims={len(claims)}); {len(set(warnings))} warning(s)")
    elif args.pack:
        version = pack_format_version(args.pack.expanduser().resolve())
        scope = "document-level Narrative grounding and structured Reference bindings" if version >= 2 else "rendering coverage"
        print(f"OK: claim provenance, audit, and {scope} are valid (claims={len(claims)}); {len(set(warnings))} warning(s)")
    else:
        print(f"OK: claim provenance and semantic-audit bindings are valid (claims={len(claims)}); {len(set(warnings))} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
