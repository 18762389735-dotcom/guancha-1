from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


ReplyStatus = Literal['answered', 'partially-answered', 'evasive', 'not-answered', 'conflicting']


@dataclass(frozen=True)
class MerchantReplyParse:
    reply_status: ReplyStatus
    answered_fields: tuple[str, ...]
    claims: tuple[dict[str, str], ...]
    unresolved_fields: tuple[str, ...]
    conflicts: tuple[str, ...]
    coverage: int
    ambiguity: int
    should_rejudge: bool
    warnings: tuple[str, ...] = ()


class MerchantReplyReasoningProvider(Protocol):
    async def parse_merchant_reply(self, *, field_key: str, raw_text: str, product_evidence: tuple[dict[str, object], ...]) -> MerchantReplyParse: ...


class FakeMerchantReplyReasoningProvider:
    """Deterministic test parser; production adapters must return this closed schema."""
    async def parse_merchant_reply(self, *, field_key: str, raw_text: str, product_evidence: tuple[dict[str, object], ...]) -> MerchantReplyParse:
        text = raw_text.lower()
        if any(token in text for token in ('不知道', '不清楚', '以实物为准')):
            return MerchantReplyParse('not-answered', (), (), (field_key,), (), 0, 0, False)
        if any(token in text for token in ('老客户', '大师', '品质很好', '高山')):
            return MerchantReplyParse('evasive', (), (), (field_key,), (), 0, 1, False)
        # Keep the offline parser deliberately small, but cover every field that
        # the question service may ask about.  A reply can remain partial; it
        # must never be turned into a made-up fact merely to unblock a decision.
        values = {
            'roast_level': [('足火', 'heavy'), ('中火', 'medium'), ('轻火', 'light'), ('浓香', 'heavy'), ('清香', 'light')],
            'aroma_style': [('兰花香', 'orchid'), ('花香', 'floral'), ('清香', 'fresh'), ('浓香', 'roasted')],
            'season': [('春茶', 'spring'), ('秋茶', 'autumn')],
            'sample_available': [],
            'return_policy': [('七天无理由', 'seven_day_return'), ('支持退货', 'return_supported'), ('不退不换', 'no_return')],
            'origin_text': [('安溪', 'anxi'), ('感德', 'gande'), ('西坪', 'xiping'), ('祥华', 'xianghua')],
            'tea_subtype': [('铁观音', 'tieguanyin'), ('黄金桂', 'huangjingui'), ('本山', 'benshan')],
        }
        if field_key == 'roast_level':
            # The merchant is answering a roast-specific question, so short
            # answers such as “浅” and “深” have an unambiguous local meaning.
            # Normalize only this closed vocabulary; free-form descriptions
            # remain unresolved instead of becoming invented evidence.
            roast_shortcuts = {
                '浅': '轻火', '浅焙': '轻火', '轻焙': '轻火', '低焙': '轻火',
                '深': '足火', '深焙': '足火', '重焙': '足火', '重火': '足火',
                '中焙': '中火',
            }
            raw_text = roast_shortcuts.get(raw_text.strip(), raw_text)
            if raw_text == raw_text.strip():
                if any(token in raw_text for token in ('\u8f7b', '\u6d45')):
                    raw_text = '\u8f7b\u706b'
                elif any(token in raw_text for token in ('\u6df1', '\u91cd', '\u6d53')):
                    raw_text = '\u8db3\u706b'
                elif '\u4e2d' in raw_text:
                    raw_text = '\u4e2d\u706b'
        elif field_key == 'sample_available':
            # Negation must win before broad positive substrings: both
            # ``没有`` and ``不提供`` contain tokens that would otherwise be
            # mistaken for a positive answer to this sample-specific question.
            negative = next((token for token in ('不提供', '没有', '不可以', '不可', '不支持') if token in raw_text), None)
            positive = next((token for token in ('可以', '可试饮', '提供', '支持', '有') if token in raw_text), None)
            if negative:
                matched = (negative, 'false')
            elif positive:
                matched = (positive, 'true')
            else:
                matched = None
        if field_key in {'price', 'weight_grams', 'year_or_batch', 'process_text'}:
            import re
            patterns = {
                'price': r'(?:￥|¥|价格\s*[:：]?)\s*(\d+(?:\.\d{1,2})?)',
                'weight_grams': r'(\d+(?:\.\d+)?)\s*(?:g|克)',
                'year_or_batch': r'((?:20)?\d{2}(?:年|春|秋)?(?:新茶|批次)?)',
                'process_text': r'(传统工艺|手工制作|炭焙|电焙|轻焙|足火)',
            }
            found = re.search(patterns[field_key], raw_text, flags=re.IGNORECASE)
            if found:
                matched = (found.group(0), found.group(1))
            else:
                matched = None
        elif field_key != 'sample_available':
            matched = next(((raw, value) for raw, value in values.get(field_key, ()) if raw in raw_text), None)
        if matched is None:
            return MerchantReplyParse('partially-answered', (), (), (field_key,), (), 0, 1, False)
        merchant_value = str(matched[1]).strip().lower()
        conflict = any(
            row.get('field_name') == field_key
            and row.get('information_status') == 'explicit'
            and row.get('normalized_value') not in (None, '', 'unknown')
            and str(row.get('normalized_value')).strip().lower() != merchant_value
            for row in product_evidence
        )
        return MerchantReplyParse('conflicting' if conflict else 'answered', (field_key,), ({'field_key': field_key, 'raw_text': matched[0], 'normalized_value': matched[1]},), () if not conflict else (field_key,), (field_key,) if conflict else (), 1, 0, True)
