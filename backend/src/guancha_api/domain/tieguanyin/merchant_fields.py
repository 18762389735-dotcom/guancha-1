"""Single P0 registry for merchant-question and reply semantics."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MerchantField:
    label: str
    decision_effect: str


MERCHANT_FIELDS = {
    "price": MerchantField("实际到手价格", "预算匹配"),
    "weight_grams": MerchantField("净含量", "性价比比较"),
    "tea_subtype": MerchantField("具体茶类", "茶类匹配"),
    "aroma_style": MerchantField("具体香型", "风味匹配"),
    "roast_level": MerchantField("具体焙火程度", "体验方向"),
    "season": MerchantField("采摘季节", "鲜爽与风格判断"),
    "origin_text": MerchantField("具体产地", "产地偏好"),
    "sample_available": MerchantField("是否提供小样或试饮装", "试错成本"),
    "return_policy": MerchantField("试饮或退换规则", "购买风险"),
    "year_or_batch": MerchantField("年份或批次", "新鲜度判断"),
    "process_text": MerchantField("制作工艺说明", "工艺偏好"),
}


def merchant_field_label(field_key: str) -> str:
    return MERCHANT_FIELDS.get(field_key, MerchantField(field_key, "当前判断")).label
